"""
Inventory API Routes

REST API for PCB component inventory, suppliers, and purchase orders.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel

import structlog
from data.inventory_service import (
    get_inventory_service,
    InventoryService,
    Component,
    Supplier,
    PurchaseOrder,
    InventoryAlert,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ComponentResponse(BaseModel):
    id: str
    part_number: str
    name: str
    category: str
    quantity: int
    reorder_point: int
    max_capacity: int
    unit_cost: float
    consumption_rate: float
    lead_time_hours: int
    supplier_id: str
    location_zone: str
    stock_level_pct: float
    is_low_stock: bool


class SupplierResponse(BaseModel):
    id: str
    name: str
    reliability_score: float
    avg_lead_time_hours: int
    min_order_quantity: int
    status: str
    

class OrderRequest(BaseModel):
    component_id: str
    quantity: int
    priority: str = "normal"  # normal, rush, urgent


class OrderResponse(BaseModel):
    id: str
    component_id: str
    supplier_id: str
    quantity: int
    unit_cost: float
    total_cost: float
    status: str
    created_at: str
    expected_delivery: str


class JITRecommendation(BaseModel):
    component_id: str
    component_name: str
    current_qty: int
    order_qty: int
    runway_hours: float
    lead_time: int
    estimated_cost: float
    priority: str


class JITResponse(BaseModel):
    orders_to_place: List[JITRecommendation]
    orders_to_expedite: List[dict]
    components_ok: List[str]
    total_cost: float


class InventoryStats(BaseModel):
    total_components: int
    low_stock_count: int
    total_value: float
    pending_orders: int
    pending_order_value: float
    active_alerts: int


# =============================================================================
# DEPENDENCY
# =============================================================================

async def get_service() -> InventoryService:
    """Get initialized inventory service."""
    service = get_inventory_service()
    if not service._initialized:
        await service.initialize()
    return service


# =============================================================================
# COMPONENT ENDPOINTS
# =============================================================================

@router.get("/components", response_model=List[ComponentResponse])
async def get_all_components(service: InventoryService = Depends(get_service)):
    """Get all PCB components in inventory."""
    components = service.get_all_components()
    return [
        ComponentResponse(
            id=c.id,
            part_number=c.part_number,
            name=c.name,
            category=c.category.value,
            quantity=c.quantity,
            reorder_point=c.reorder_point,
            max_capacity=c.max_capacity,
            unit_cost=c.unit_cost,
            consumption_rate=c.consumption_rate,
            lead_time_hours=c.lead_time_hours,
            supplier_id=c.supplier_id,
            location_zone=c.location_zone,
            stock_level_pct=round((c.quantity / c.max_capacity) * 100, 1),
            is_low_stock=c.quantity <= c.reorder_point
        )
        for c in components
    ]


@router.get("/components/low-stock", response_model=List[ComponentResponse])
async def get_low_stock_components(service: InventoryService = Depends(get_service)):
    """Get components below reorder point."""
    components = service.get_low_stock_components()
    return [
        ComponentResponse(
            id=c.id,
            part_number=c.part_number,
            name=c.name,
            category=c.category.value,
            quantity=c.quantity,
            reorder_point=c.reorder_point,
            max_capacity=c.max_capacity,
            unit_cost=c.unit_cost,
            consumption_rate=c.consumption_rate,
            lead_time_hours=c.lead_time_hours,
            supplier_id=c.supplier_id,
            location_zone=c.location_zone,
            stock_level_pct=round((c.quantity / c.max_capacity) * 100, 1),
            is_low_stock=True
        )
        for c in components
    ]


@router.get("/components/{component_id}", response_model=ComponentResponse)
async def get_component(component_id: str, service: InventoryService = Depends(get_service)):
    """Get a specific component by ID."""
    comp = service.get_component(component_id)
    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component {component_id} not found"
        )
    return ComponentResponse(
        id=comp.id,
        part_number=comp.part_number,
        name=comp.name,
        category=comp.category.value,
        quantity=comp.quantity,
        reorder_point=comp.reorder_point,
        max_capacity=comp.max_capacity,
        unit_cost=comp.unit_cost,
        consumption_rate=comp.consumption_rate,
        lead_time_hours=comp.lead_time_hours,
        supplier_id=comp.supplier_id,
        location_zone=comp.location_zone,
        stock_level_pct=round((comp.quantity / comp.max_capacity) * 100, 1),
        is_low_stock=comp.quantity <= comp.reorder_point
    )


@router.post("/components/{component_id}/consume")
async def consume_component(
    component_id: str, 
    quantity: int,
    service: InventoryService = Depends(get_service)
):
    """Consume a quantity of a component (for production)."""
    comp = await service.update_quantity(component_id, -quantity)
    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component {component_id} not found"
        )
    return {
        "success": True,
        "component_id": component_id,
        "consumed": quantity,
        "remaining": comp.quantity
    }


@router.post("/components/{component_id}/restock")
async def restock_component(
    component_id: str, 
    quantity: int,
    service: InventoryService = Depends(get_service)
):
    """Add quantity to a component (for manual restock)."""
    comp = await service.update_quantity(component_id, quantity)
    if not comp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component {component_id} not found"
        )
    return {
        "success": True,
        "component_id": component_id,
        "added": quantity,
        "new_quantity": comp.quantity
    }


# =============================================================================
# SUPPLIER ENDPOINTS
# =============================================================================

@router.get("/suppliers", response_model=List[SupplierResponse])
async def get_all_suppliers(service: InventoryService = Depends(get_service)):
    """Get all suppliers."""
    suppliers = service.get_all_suppliers()
    return [
        SupplierResponse(
            id=s.id,
            name=s.name,
            reliability_score=round(s.reliability_score, 1),
            avg_lead_time_hours=s.avg_lead_time_hours,
            min_order_quantity=s.min_order_quantity,
            status=s.status
        )
        for s in suppliers
    ]


@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: str, service: InventoryService = Depends(get_service)):
    """Get a specific supplier."""
    supplier = service.get_supplier(supplier_id)
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier {supplier_id} not found"
        )
    return SupplierResponse(
        id=supplier.id,
        name=supplier.name,
        reliability_score=round(supplier.reliability_score, 1),
        avg_lead_time_hours=supplier.avg_lead_time_hours,
        min_order_quantity=supplier.min_order_quantity,
        status=supplier.status
    )


# =============================================================================
# ORDER ENDPOINTS
# =============================================================================

@router.post("/orders", response_model=OrderResponse)
async def create_order(request: OrderRequest, service: InventoryService = Depends(get_service)):
    """Create a new purchase order."""
    order = await service.create_purchase_order(
        component_id=request.component_id,
        quantity=request.quantity,
        priority=request.priority
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create order - check component and supplier"
        )
    return OrderResponse(
        id=order.id,
        component_id=order.component_id,
        supplier_id=order.supplier_id,
        quantity=order.quantity,
        unit_cost=order.unit_cost,
        total_cost=order.total_cost,
        status=order.status.value,
        created_at=order.created_at.isoformat(),
        expected_delivery=order.expected_delivery.isoformat()
    )


@router.get("/orders", response_model=List[OrderResponse])
async def get_pending_orders(service: InventoryService = Depends(get_service)):
    """Get all pending purchase orders."""
    orders = service.get_pending_orders()
    return [
        OrderResponse(
            id=o.id,
            component_id=o.component_id,
            supplier_id=o.supplier_id,
            quantity=o.quantity,
            unit_cost=o.unit_cost,
            total_cost=o.total_cost,
            status=o.status.value,
            created_at=o.created_at.isoformat(),
            expected_delivery=o.expected_delivery.isoformat()
        )
        for o in orders
    ]


@router.post("/orders/{order_id}/receive")
async def receive_order(order_id: str, service: InventoryService = Depends(get_service)):
    """Mark an order as received and add to inventory."""
    order = await service.receive_delivery(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found"
        )
    return {
        "success": True,
        "order_id": order_id,
        "quantity_received": order.quantity,
        "component_id": order.component_id
    }


# =============================================================================
# JIT OPTIMIZATION ENDPOINTS
# =============================================================================

@router.get("/jit/recommendations", response_model=JITResponse)
async def get_jit_recommendations(service: InventoryService = Depends(get_service)):
    """
    Get JIT ordering recommendations based on current inventory
    and consumption rates.
    """
    recommendations = await service.run_jit_optimization()
    return JITResponse(
        orders_to_place=[
            JITRecommendation(**r) for r in recommendations["orders_to_place"]
        ],
        orders_to_expedite=recommendations["orders_to_expedite"],
        components_ok=recommendations["components_ok"],
        total_cost=recommendations["total_cost"]
    )


@router.post("/jit/auto-order")
async def execute_jit_orders(service: InventoryService = Depends(get_service)):
    """
    Execute JIT orders automatically based on recommendations.
    This is what the Embodied Agent would trigger in solution mode.
    """
    recommendations = await service.run_jit_optimization()
    orders_created = []
    
    for rec in recommendations["orders_to_place"]:
        order = await service.create_purchase_order(
            component_id=rec["component_id"],
            quantity=rec["order_qty"],
            priority=rec["priority"]
        )
        if order:
            orders_created.append({
                "order_id": order.id,
                "component": rec["component_name"],
                "quantity": order.quantity,
                "expected_delivery": order.expected_delivery.isoformat()
            })
    
    return {
        "success": True,
        "orders_created": len(orders_created),
        "orders": orders_created,
        "total_cost": recommendations["total_cost"]
    }


# =============================================================================
# ALERTS ENDPOINT
# =============================================================================

@router.get("/alerts")
async def get_inventory_alerts(service: InventoryService = Depends(get_service)):
    """Get active inventory alerts."""
    alerts = service.get_active_alerts()
    return [
        {
            "id": a.id,
            "component_id": a.component_id,
            "component_name": a.component_name,
            "current_quantity": a.current_quantity,
            "reorder_point": a.reorder_point,
            "hours_until_stockout": round(a.hours_until_stockout, 1),
            "recommended_order_qty": a.recommended_order_qty,
            "priority": a.priority,
            "created_at": a.created_at.isoformat()
        }
        for a in alerts
    ]


# =============================================================================
# STATS ENDPOINT
# =============================================================================

@router.get("/stats", response_model=InventoryStats)
async def get_inventory_stats(service: InventoryService = Depends(get_service)):
    """Get inventory statistics summary."""
    components = service.get_all_components()
    low_stock = service.get_low_stock_components()
    pending_orders = service.get_pending_orders()
    alerts = service.get_active_alerts()
    
    total_value = sum(c.quantity * c.unit_cost for c in components)
    pending_value = sum(o.total_cost for o in pending_orders)
    
    return InventoryStats(
        total_components=len(components),
        low_stock_count=len(low_stock),
        total_value=round(total_value, 2),
        pending_orders=len(pending_orders),
        pending_order_value=round(pending_value, 2),
        active_alerts=len(alerts)
    )
