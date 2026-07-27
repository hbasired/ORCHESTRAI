"""
Supabase Inventory Service

Manages PCB component inventory, suppliers, and purchase orders
with JIT (Just-In-Time) ordering optimization.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import structlog
from pydantic import BaseModel, Field
from enum import Enum

logger = structlog.get_logger(__name__)

# Try importing Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase not available, using mock data")


# =============================================================================
# MODELS
# =============================================================================

class ComponentCategory(str, Enum):
    PASSIVE = "passive"  # Resistors, capacitors, inductors
    IC = "ic"            # Integrated circuits
    CONNECTOR = "connector"
    BOARD = "board"      # PCB blanks
    CONSUMABLE = "consumable"  # Solder paste, etc.


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Component(BaseModel):
    """PCB Component inventory item."""
    id: str
    part_number: str
    name: str
    category: ComponentCategory
    quantity: int
    reorder_point: int
    max_capacity: int
    unit_cost: float
    consumption_rate: float  # units per hour
    lead_time_hours: int
    supplier_id: str
    location_zone: str = "warehouse"
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class Supplier(BaseModel):
    """Component supplier."""
    id: str
    name: str
    reliability_score: float  # 0-100
    avg_lead_time_hours: int
    min_order_quantity: int
    status: str = "active"
    contact_email: Optional[str] = None
    last_delivery: Optional[datetime] = None


class PurchaseOrder(BaseModel):
    """Purchase order for components."""
    id: str
    component_id: str
    supplier_id: str
    quantity: int
    unit_cost: float
    total_cost: float
    status: OrderStatus
    created_at: datetime
    expected_delivery: datetime
    actual_delivery: Optional[datetime] = None
    notes: Optional[str] = None


class InventoryAlert(BaseModel):
    """Low stock or urgent order alert."""
    id: str
    component_id: str
    component_name: str
    current_quantity: int
    reorder_point: int
    hours_until_stockout: float
    recommended_order_qty: int
    priority: str  # low, medium, high, critical
    created_at: datetime


# =============================================================================
# MOCK DATA
# =============================================================================

MOCK_COMPONENTS = [
    Component(
        id="comp_001", part_number="RC0402FR-0710KL", name="Resistor 10K 0402",
        category=ComponentCategory.PASSIVE, quantity=45000, reorder_point=10000,
        max_capacity=100000, unit_cost=0.002, consumption_rate=500,
        lead_time_hours=48, supplier_id="sup_001", location_zone="zone_a"
    ),
    Component(
        id="comp_002", part_number="CC0603KRX7R9BB104", name="Capacitor 100nF 0603",
        category=ComponentCategory.PASSIVE, quantity=32000, reorder_point=8000,
        max_capacity=80000, unit_cost=0.005, consumption_rate=350,
        lead_time_hours=48, supplier_id="sup_001", location_zone="zone_a"
    ),
    Component(
        id="comp_003", part_number="STM32F407VGT6", name="STM32F4 MCU",
        category=ComponentCategory.IC, quantity=850, reorder_point=200,
        max_capacity=2000, unit_cost=8.50, consumption_rate=20,
        lead_time_hours=168, supplier_id="sup_002", location_zone="zone_b"
    ),
    Component(
        id="comp_004", part_number="W25Q128JVSIQ", name="Flash Memory 128Mb",
        category=ComponentCategory.IC, quantity=620, reorder_point=150,
        max_capacity=1500, unit_cost=2.20, consumption_rate=15,
        lead_time_hours=120, supplier_id="sup_002", location_zone="zone_b"
    ),
    Component(
        id="comp_005", part_number="USB-C-SMD-24P", name="USB-C Connector",
        category=ComponentCategory.CONNECTOR, quantity=2800, reorder_point=500,
        max_capacity=5000, unit_cost=0.35, consumption_rate=40,
        lead_time_hours=72, supplier_id="sup_003", location_zone="zone_c"
    ),
    Component(
        id="comp_006", part_number="PCB-4L-100x80", name="4-Layer PCB 100x80mm",
        category=ComponentCategory.BOARD, quantity=450, reorder_point=100,
        max_capacity=1000, unit_cost=4.50, consumption_rate=25,
        lead_time_hours=120, supplier_id="sup_004", location_zone="zone_d"
    ),
    Component(
        id="comp_007", part_number="SAC305-T4-500G", name="Solder Paste SAC305",
        category=ComponentCategory.CONSUMABLE, quantity=12, reorder_point=5,
        max_capacity=50, unit_cost=85.00, consumption_rate=0.5,
        lead_time_hours=24, supplier_id="sup_001", location_zone="zone_a"
    ),
]

MOCK_SUPPLIERS = [
    Supplier(
        id="sup_001", name="Alpha Electronics",
        reliability_score=95.5, avg_lead_time_hours=48,
        min_order_quantity=1000, status="active",
        contact_email="orders@alpha-elec.com"
    ),
    Supplier(
        id="sup_002", name="Micro Components Ltd",
        reliability_score=88.2, avg_lead_time_hours=120,
        min_order_quantity=100, status="active",
        contact_email="sales@microcomp.com"
    ),
    Supplier(
        id="sup_003", name="Connector World",
        reliability_score=92.0, avg_lead_time_hours=72,
        min_order_quantity=500, status="active"
    ),
    Supplier(
        id="sup_004", name="PCB Factory Co",
        reliability_score=90.5, avg_lead_time_hours=120,
        min_order_quantity=50, status="active"
    ),
]


# =============================================================================
# INVENTORY SERVICE
# =============================================================================

class InventoryService:
    """
    Manages PCB component inventory with Supabase persistence.
    Implements JIT ordering with production rate awareness.
    """
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        self.client: Optional[Client] = None
        self._initialized = False
        
        # Local cache
        self._components: Dict[str, Component] = {}
        self._suppliers: Dict[str, Supplier] = {}
        self._orders: Dict[str, PurchaseOrder] = {}
        self._alerts: List[InventoryAlert] = []
        
        if supabase_url and supabase_key and SUPABASE_AVAILABLE:
            try:
                self.client = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized for inventory")
            except Exception as e:
                logger.error("Supabase connection failed", error=str(e))
    
    async def initialize(self) -> bool:
        """Initialize inventory data from Supabase or mock data."""
        try:
            if self.client:
                await self._sync_from_supabase()
            else:
                self._load_mock_data()
            
            self._initialized = True
            logger.info("Inventory service initialized", 
                       components=len(self._components),
                       suppliers=len(self._suppliers))
            return True
        except Exception as e:
            logger.error("Inventory initialization failed", error=str(e))
            self._load_mock_data()
            return True
    
    def _load_mock_data(self):
        """Load mock data for development."""
        for comp in MOCK_COMPONENTS:
            self._components[comp.id] = comp
        for sup in MOCK_SUPPLIERS:
            self._suppliers[sup.id] = sup
    
    async def _sync_from_supabase(self):
        """Sync data from Supabase tables."""
        if not self.client:
            return
        
        try:
            # Fetch components
            result = self.client.table("pcb_components").select("*").execute()
            for row in result.data:
                self._components[row["id"]] = Component(**row)
            
            # Fetch suppliers
            result = self.client.table("suppliers").select("*").execute()
            for row in result.data:
                self._suppliers[row["id"]] = Supplier(**row)
            
            # Fetch active orders
            result = self.client.table("purchase_orders").select("*").eq("status", "pending").execute()
            for row in result.data:
                self._orders[row["id"]] = PurchaseOrder(**row)
                
        except Exception as e:
            logger.error("Supabase sync failed", error=str(e))
            self._load_mock_data()
    
    # -------------------------------------------------------------------------
    # COMPONENT OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_all_components(self) -> List[Component]:
        """Get all components in inventory."""
        return list(self._components.values())
    
    def get_component(self, component_id: str) -> Optional[Component]:
        """Get a specific component by ID."""
        return self._components.get(component_id)
    
    def get_low_stock_components(self) -> List[Component]:
        """Get components below reorder point."""
        return [c for c in self._components.values() 
                if c.quantity <= c.reorder_point]
    
    async def update_quantity(self, component_id: str, delta: int) -> Optional[Component]:
        """
        Update component quantity (positive for add, negative for consume).
        """
        comp = self._components.get(component_id)
        if not comp:
            return None
        
        new_qty = max(0, min(comp.max_capacity, comp.quantity + delta))
        comp.quantity = new_qty
        comp.last_updated = datetime.utcnow()
        
        # Persist to Supabase
        if self.client:
            try:
                self.client.table("pcb_components").update({
                    "quantity": new_qty,
                    "last_updated": comp.last_updated.isoformat()
                }).eq("id", component_id).execute()
            except Exception as e:
                logger.error("Failed to update quantity in Supabase", error=str(e))
        
        # Check for alerts
        if comp.quantity <= comp.reorder_point:
            await self._create_low_stock_alert(comp)
        
        return comp
    
    async def consume_for_production(self, production_rate: float = 1.0) -> Dict[str, int]:
        """
        Consume components based on production rate.
        Returns dict of component_id -> consumed quantity.
        """
        consumed = {}
        for comp_id, comp in self._components.items():
            consume_qty = int(comp.consumption_rate * production_rate)
            if consume_qty > 0:
                await self.update_quantity(comp_id, -consume_qty)
                consumed[comp_id] = consume_qty
        return consumed
    
    # -------------------------------------------------------------------------
    # SUPPLIER OPERATIONS
    # -------------------------------------------------------------------------
    
    def get_all_suppliers(self) -> List[Supplier]:
        """Get all suppliers."""
        return list(self._suppliers.values())
    
    def get_supplier(self, supplier_id: str) -> Optional[Supplier]:
        """Get a specific supplier."""
        return self._suppliers.get(supplier_id)
    
    def get_best_supplier_for_component(self, component_id: str) -> Optional[Supplier]:
        """Get the best supplier for a component based on reliability and lead time."""
        comp = self._components.get(component_id)
        if not comp:
            return None
        return self._suppliers.get(comp.supplier_id)
    
    # -------------------------------------------------------------------------
    # ORDER OPERATIONS
    # -------------------------------------------------------------------------
    
    async def create_purchase_order(
        self, 
        component_id: str, 
        quantity: int,
        priority: str = "normal"
    ) -> Optional[PurchaseOrder]:
        """
        Create a new purchase order for a component.
        Uses JIT principles - orders based on actual need.
        """
        comp = self._components.get(component_id)
        if not comp:
            logger.error("Component not found for order", component_id=component_id)
            return None
        
        supplier = self._suppliers.get(comp.supplier_id)
        if not supplier:
            logger.error("Supplier not found", supplier_id=comp.supplier_id)
            return None
        
        # Calculate optimal quantity
        order_qty = max(quantity, supplier.min_order_quantity)
        
        # Adjust lead time based on priority
        lead_time = supplier.avg_lead_time_hours
        if priority == "urgent":
            lead_time = int(lead_time * 0.5)
        elif priority == "rush":
            lead_time = int(lead_time * 0.75)
        
        order = PurchaseOrder(
            id=f"po_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{component_id}",
            component_id=component_id,
            supplier_id=supplier.id,
            quantity=order_qty,
            unit_cost=comp.unit_cost,
            total_cost=order_qty * comp.unit_cost,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow(),
            expected_delivery=datetime.utcnow() + timedelta(hours=lead_time),
            notes=f"Priority: {priority}"
        )
        
        self._orders[order.id] = order
        
        # Persist to Supabase
        if self.client:
            try:
                self.client.table("purchase_orders").insert(order.model_dump()).execute()
            except Exception as e:
                logger.error("Failed to create order in Supabase", error=str(e))
        
        logger.info("Purchase order created", 
                   order_id=order.id, 
                   component=comp.name,
                   quantity=order_qty,
                   expected_delivery=order.expected_delivery.isoformat())
        
        return order
    
    def get_pending_orders(self) -> List[PurchaseOrder]:
        """Get all pending purchase orders."""
        return [o for o in self._orders.values() 
                if o.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.SHIPPED]]
    
    async def receive_delivery(self, order_id: str) -> Optional[PurchaseOrder]:
        """Mark an order as delivered and add to inventory."""
        order = self._orders.get(order_id)
        if not order:
            return None
        
        order.status = OrderStatus.DELIVERED
        order.actual_delivery = datetime.utcnow()
        
        # Add to inventory
        await self.update_quantity(order.component_id, order.quantity)
        
        # Update supplier reliability
        supplier = self._suppliers.get(order.supplier_id)
        if supplier:
            # Was delivery on time?
            if order.actual_delivery <= order.expected_delivery:
                supplier.reliability_score = min(100, supplier.reliability_score + 0.5)
            else:
                supplier.reliability_score = max(0, supplier.reliability_score - 2.0)
            supplier.last_delivery = order.actual_delivery
        
        logger.info("Delivery received", order_id=order_id, quantity=order.quantity)
        return order
    
    # -------------------------------------------------------------------------
    # ALERTS & JIT OPTIMIZATION
    # -------------------------------------------------------------------------
    
    async def _create_low_stock_alert(self, comp: Component):
        """Create alert for low stock component."""
        hours_until_stockout = comp.quantity / comp.consumption_rate if comp.consumption_rate > 0 else 999
        
        # Determine priority
        if hours_until_stockout < 4:
            priority = "critical"
        elif hours_until_stockout < 8:
            priority = "high"
        elif hours_until_stockout < 24:
            priority = "medium"
        else:
            priority = "low"
        
        # Calculate recommended order quantity (cover 2 weeks + safety stock)
        recommended_qty = int(comp.consumption_rate * 24 * 14 * 1.2)
        
        alert = InventoryAlert(
            id=f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{comp.id}",
            component_id=comp.id,
            component_name=comp.name,
            current_quantity=comp.quantity,
            reorder_point=comp.reorder_point,
            hours_until_stockout=hours_until_stockout,
            recommended_order_qty=recommended_qty,
            priority=priority,
            created_at=datetime.utcnow()
        )
        
        self._alerts.append(alert)
        
        # Auto-order for critical items in solution mode
        # This would be triggered by the Embodied Agent in coordination
        
        return alert
    
    def get_active_alerts(self) -> List[InventoryAlert]:
        """Get all active inventory alerts."""
        # Filter to recent alerts (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        return [a for a in self._alerts if a.created_at > cutoff]
    
    async def run_jit_optimization(self, production_schedule: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Run JIT optimization based on production schedule.
        Returns recommendations for orders.
        """
        recommendations = {
            "orders_to_place": [],
            "orders_to_expedite": [],
            "components_ok": [],
            "total_cost": 0.0
        }
        
        for comp in self._components.values():
            # Calculate runway (hours until stockout)
            if comp.consumption_rate > 0:
                runway = comp.quantity / comp.consumption_rate
            else:
                runway = 999
            
            supplier = self._suppliers.get(comp.supplier_id)
            lead_time = supplier.avg_lead_time_hours if supplier else 72
            
            # If runway < lead_time + safety buffer, need to order
            safety_buffer = 8  # hours
            if runway < lead_time + safety_buffer:
                order_qty = int(comp.consumption_rate * 24 * 7)  # 1 week of stock
                recommendations["orders_to_place"].append({
                    "component_id": comp.id,
                    "component_name": comp.name,
                    "current_qty": comp.quantity,
                    "order_qty": order_qty,
                    "runway_hours": runway,
                    "lead_time": lead_time,
                    "estimated_cost": order_qty * comp.unit_cost,
                    "priority": "urgent" if runway < safety_buffer else "normal"
                })
                recommendations["total_cost"] += order_qty * comp.unit_cost
            else:
                recommendations["components_ok"].append(comp.id)
        
        return recommendations


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_inventory_service: Optional[InventoryService] = None


def get_inventory_service() -> InventoryService:
    """Get or create the inventory service singleton."""
    global _inventory_service
    if _inventory_service is None:
        from config import settings
        _inventory_service = InventoryService(
            supabase_url=getattr(settings, "SUPABASE_URL", None),
            supabase_key=getattr(settings, "SUPABASE_KEY", None)
        )
    return _inventory_service


async def init_inventory_service() -> InventoryService:
    """Initialize and return the inventory service."""
    service = get_inventory_service()
    await service.initialize()
    return service
