from playwright.sync_api import sync_playwright
from django.template.loader import render_to_string


def generate_invoice_pdf(order):
    import os
    from django.conf import settings
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    logo_url = f"file:///{logo_path.replace(os.sep, '/')}" if os.path.exists(logo_path) else None

    context = {
        "order": order,
        "items": order.items.all(),  # related_name="items"
        "logo_url": logo_url,
    }
    
    html = render_to_string("invoice.html", context)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={
                "width": 1240,   # A4 width equivalent
                "height": 1754   # A4 height equivalent
            }
        )

        page.set_content(html, wait_until="networkidle")

        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            prefer_css_page_size=True
        )

        browser.close()

    return pdf_bytes
