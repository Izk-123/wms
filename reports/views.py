from django.views.generic import ListView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta, date

from inventory.models import Item, Stock, StockMovement, Warehouse, Category
from procurement.models import PurchaseOrder, GoodsReceipt
from operations.models import Project, MaterialRequest
from assets.models import Asset
from accounts.models import User


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def get_dashboard_stats():
    """Central function — used by dashboard and HTMX partial."""
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # ── Chart data — last 7 days ─────────────────────
    from django.db.models.functions import TruncDate
    chart_in  = []
    chart_out = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_in = StockMovement.objects.filter(
            movement_type='IN', created_at__date=day
        ).count()
        day_out = StockMovement.objects.filter(
            movement_type='OUT', created_at__date=day
        ).count()
        chart_in.append(day_in)
        chart_out.append(day_out)

    # Inventory
    total_items = Item.objects.filter(is_active=True).count()
    total_warehouses = Warehouse.objects.filter(is_active=True).count()
    low_stock_items = Stock.objects.filter(
        quantity__lte=F('item__minimum_stock'),
        item__minimum_stock__gt=0
    ).select_related('item', 'warehouse')
    low_stock_count = low_stock_items.count()

    # Stock value
    stock_value = Stock.objects.aggregate(
        total=Sum(F('quantity') * F('item__unit_cost'))
    )['total'] or 0

    # Movements today
    received_today = StockMovement.objects.filter(
        movement_type='IN',
        created_at__date=today
    ).count()
    issued_today = StockMovement.objects.filter(
        movement_type='OUT',
        created_at__date=today
    ).count()

    # Procurement
    pending_orders = PurchaseOrder.objects.filter(
        status__in=('draft', 'sent')
    ).count()
    pending_approvals = MaterialRequest.objects.filter(
        status='submitted'
    ).count()

    # Projects
    active_projects = Project.objects.filter(status='active').count()

    # Assets
    assets_assigned = Asset.objects.filter(status='assigned').count()
    assets_due_maintenance = Asset.objects.filter(
        next_maintenance_date__lte=today + timedelta(days=7),
        next_maintenance_date__isnull=False,
        status__in=('available', 'assigned')
    ).count()

    # Recent movements
    recent_movements = StockMovement.objects.select_related(
        'item', 'warehouse', 'created_by'
    ).order_by('-created_at')[:8]

    return {
        'total_items': total_items,
        'total_warehouses': total_warehouses,
        'low_stock_count': low_stock_count,
        'low_stock_items': low_stock_items[:5],
        'stock_value': stock_value,
        'received_today': received_today,
        'issued_today': issued_today,
        'pending_orders': pending_orders,
        'pending_approvals': pending_approvals,
        'active_projects': active_projects,
        'assets_assigned': assets_assigned,
        'assets_due_maintenance': assets_due_maintenance,
        'recent_movements': recent_movements,
        'movement_chart_in':  chart_in,
        'movement_chart_out': chart_out,
        'today': today,
    }


# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(get_dashboard_stats())
        return ctx


class DashboardStatsPartialView(LoginRequiredMixin, View):
    """HTMX endpoint — refreshes stat cards every 30s."""

    def get(self, request):
        context = get_dashboard_stats()
        return render(request, 'reports/partials/dashboard_stats.html', context)


# ─────────────────────────────────────────
# INVENTORY REPORTS
# ─────────────────────────────────────────

class InventoryReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/inventory_report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        warehouse_id = self.request.GET.get('warehouse')
        category_id = self.request.GET.get('category')
        show = self.request.GET.get('show', 'all')

        stocks = Stock.objects.select_related(
            'item', 'item__category', 'item__unit', 'warehouse'
        ).order_by('item__name')

        if warehouse_id:
            stocks = stocks.filter(warehouse_id=warehouse_id)
        if category_id:
            stocks = stocks.filter(item__category_id=category_id)
        if show == 'low':
            stocks = stocks.filter(
                quantity__lte=F('item__minimum_stock'),
                item__minimum_stock__gt=0
            )
        elif show == 'zero':
            stocks = stocks.filter(quantity=0)

        total_value = stocks.aggregate(
            total=Sum(F('quantity') * F('item__unit_cost'))
        )['total'] or 0

        ctx.update({
            'stocks': stocks,
            'total_value': total_value,
            'warehouses': Warehouse.objects.filter(is_active=True),
            'categories': Category.objects.all(),
            'selected_warehouse': warehouse_id or '',
            'selected_category': category_id or '',
            'show': show,
        })
        return ctx


class StockMovementReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/movement_report.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()

        date_from = self.request.GET.get('date_from', str(today - timedelta(days=30)))
        date_to = self.request.GET.get('date_to', str(today))
        movement_type = self.request.GET.get('type', '')
        warehouse_id = self.request.GET.get('warehouse', '')

        movements = StockMovement.objects.select_related(
            'item', 'item__unit', 'warehouse', 'created_by'
        ).filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to
        ).order_by('-created_at')

        if movement_type:
            movements = movements.filter(movement_type=movement_type)
        if warehouse_id:
            movements = movements.filter(warehouse_id=warehouse_id)

        ctx.update({
            'movements': movements,
            'date_from': date_from,
            'date_to': date_to,
            'movement_types': StockMovement.MOVEMENT_TYPES,
            'warehouses': Warehouse.objects.filter(is_active=True),
            'selected_type': movement_type,
            'selected_warehouse': warehouse_id,
            'total_in': movements.filter(
                movement_type='IN'
            ).aggregate(t=Sum('quantity'))['t'] or 0,
            'total_out': movements.filter(
                movement_type='OUT'
            ).aggregate(t=Sum('quantity'))['t'] or 0,
        })
        return ctx


class ProjectConsumptionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/project_consumption.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project_id = self.request.GET.get('project')

        projects = Project.objects.filter(status='active')
        selected_project = None
        consumption = []

        if project_id:
            selected_project = Project.objects.filter(pk=project_id).first()
            if selected_project:
                for mr in selected_project.material_requests.filter(
                    status__in=('issued', 'partially_issued')
                ).prefetch_related('items__item__unit'):
                    for item in mr.items.all():
                        if item.quantity_issued > 0:
                            consumption.append({
                                'item': item.item,
                                'quantity': item.quantity_issued,
                                'cost': item.quantity_issued * item.item.unit_cost,
                                'reference': mr.reference,
                                'date': mr.created_at,
                            })

        ctx.update({
            'projects': projects,
            'selected_project': selected_project,
            'consumption': consumption,
            'total_cost': sum(c['cost'] for c in consumption),
        })
        return ctx


# ─────────────────────────────────────────
# EXCEL EXPORTS
# ─────────────────────────────────────────

class ExportInventoryExcelView(LoginRequiredMixin, View):
    def get(self, request):
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Inventory Report"

        # Header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="1E293B",
            end_color="1E293B",
            fill_type="solid"
        )

        headers = [
            'SKU', 'Item Name', 'Category', 'Type',
            'Unit', 'Warehouse', 'Quantity',
            'Min Stock', 'Unit Cost (MWK)', 'Total Value (MWK)', 'Status'
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        # Data
        stocks = Stock.objects.select_related(
            'item', 'item__category', 'item__unit', 'warehouse'
        ).order_by('item__name')

        for row, stock in enumerate(stocks, 2):
            total_value = stock.quantity * stock.item.unit_cost
            status = "Low Stock" if stock.is_low_stock else "OK"
            ws.append([
                stock.item.sku,
                stock.item.name,
                stock.item.category.name,
                stock.item.get_item_type_display(),
                stock.item.unit.symbol,
                stock.warehouse.name,
                float(stock.quantity),
                float(stock.item.minimum_stock),
                float(stock.item.unit_cost),
                float(total_value),
                status,
            ])

        # Column widths
        column_widths = [12, 35, 20, 18, 8, 20, 12, 12, 18, 18, 12]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[
                openpyxl.utils.get_column_letter(col)
            ].width = width

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="inventory_report_{date.today()}.xlsx"'
        )
        wb.save(response)
        return response


class ExportMovementsExcelView(LoginRequiredMixin, View):
    def get(self, request):
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Stock Movements"

        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="1E293B",
            end_color="1E293B",
            fill_type="solid"
        )

        headers = [
            'Date', 'Item', 'SKU', 'Type',
            'Quantity', 'Unit', 'Warehouse',
            'Reference', 'Recorded By'
        ]

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')

        today = timezone.now().date()
        date_from = request.GET.get(
            'date_from', str(today - timedelta(days=30))
        )
        date_to = request.GET.get('date_to', str(today))

        movements = StockMovement.objects.select_related(
            'item', 'item__unit', 'warehouse', 'created_by'
        ).filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to
        ).order_by('-created_at')

        for movement in movements:
            ws.append([
                movement.created_at.strftime('%d/%m/%Y %H:%M'),
                movement.item.name,
                movement.item.sku,
                movement.movement_type,
                float(movement.quantity),
                movement.item.unit.symbol,
                movement.warehouse.name,
                movement.reference or '',
                movement.created_by.get_full_name(),
            ])

        column_widths = [18, 35, 12, 12, 12, 8, 20, 18, 25]
        for col, width in enumerate(column_widths, 1):
            ws.column_dimensions[
                openpyxl.utils.get_column_letter(col)
            ].width = width

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="movements_{date_from}_to_{date_to}.xlsx"'
        )
        wb.save(response)
        return response


# ─────────────────────────────────────────
# PDF EXPORTS
# ─────────────────────────────────────────

class ExportInventoryPDFView(LoginRequiredMixin, View):
    def get(self, request):
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle,
            Paragraph, Spacer
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="inventory_{date.today()}.pdf"'
        )

        doc = SimpleDocTemplate(
            response,
            pagesize=landscape(A4),
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=2*cm,
            bottomMargin=1.5*cm
        )

        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=6,
        )
        elements.append(
            Paragraph("J&N Warehouse Management System", title_style)
        )
        elements.append(
            Paragraph(
                f"Inventory Report — {date.today().strftime('%d %B %Y')}",
                styles['Normal']
            )
        )
        elements.append(Spacer(1, 0.5*cm))

        # Table data
        data = [[
            'SKU', 'Item Name', 'Category',
            'Warehouse', 'Qty', 'Unit',
            'Min Stock', 'Unit Cost', 'Total Value', 'Status'
        ]]

        stocks = Stock.objects.select_related(
            'item', 'item__category',
            'item__unit', 'warehouse'
        ).order_by('item__name')

        total_value = 0
        for stock in stocks:
            value = stock.quantity * stock.item.unit_cost
            total_value += value
            data.append([
                stock.item.sku,
                stock.item.name[:35],
                stock.item.category.name[:20],
                stock.warehouse.name[:20],
                f"{stock.quantity:,.2f}",
                stock.item.unit.symbol,
                f"{stock.item.minimum_stock:,.2f}",
                f"MWK {stock.item.unit_cost:,.2f}",
                f"MWK {value:,.2f}",
                "⚠ Low" if stock.is_low_stock else "OK",
            ])

        # Total row
        data.append([
            '', '', '', 'TOTAL', '', '', '', '',
            f"MWK {total_value:,.2f}", ''
        ])

        table = Table(
            data,
            colWidths=[
                2.2*cm, 6*cm, 3.5*cm, 3.5*cm,
                1.8*cm, 1.4*cm, 2*cm, 3.2*cm, 3.5*cm, 1.8*cm
            ]
        )

        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),

            # Data rows
            ('FONTSIZE', (0, 1), (-1, -1), 7.5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2),
             [colors.white, colors.HexColor('#F8FAFC')]),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),

            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))

        elements.append(table)
        doc.build(elements)
        return response
    
class GlobalSearchView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        results = {}

        if len(q) >= 2:
            from inventory.models import Item, Warehouse
            from procurement.models import Supplier, PurchaseOrder
            from operations.models import Project

            results['items'] = Item.objects.filter(
                Q(name__icontains=q) | Q(sku__icontains=q)
            )[:5]

            results['warehouses'] = Warehouse.objects.filter(
                name__icontains=q
            )[:3]

            results['suppliers'] = Supplier.objects.filter(
                name__icontains=q
            )[:3]

            results['projects'] = Project.objects.filter(
                Q(name__icontains=q) | Q(code__icontains=q)
            )[:3]

            results['orders'] = PurchaseOrder.objects.filter(
                reference__icontains=q
            )[:3]

        from django.template.loader import render_to_string
        from django.http import HttpResponse
        html = render_to_string(
            'reports/partials/search_results.html',
            {'results': results, 'q': q},
            request=request
        )
        return HttpResponse(html)