from flask import Flask, render_template, request, Response, session, redirect, url_for
from functools import wraps
from reportlab.lib.pagesizes import letter, inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, Flowable
from reportlab.lib.styles import getSampleStyleSheet
import io

app = Flask(__name__)
app.secret_key = "limasportinggoods"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("logged_in") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

class LongLine(Flowable):
    def __init__(self, width, thickness, color):
        Flowable.__init__(self)
        self.width = width
        self.thickness = thickness
        self.color = color

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == 'rob' and request.form['password'] == 'titos':
            session['logged_in'] = True
            return redirect(url_for('invoice'))
        else:
            error = 'Invalid credentials. Please try again.'
    if session.get("logged_in"):
        return redirect(url_for('invoice'))
    return render_template('login.html', error=error)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    if session.get("logged_in"):
        return redirect(url_for('invoice'))
    return redirect(url_for('login'))

@app.route('/invoice', methods=['GET', 'POST'])
@login_required
def invoice():
    products = []
    subtotal = 0
    tax_amount = 0
    total_with_tax = 0
    
    num_items = 1
    author = None

    if request.method == 'POST':
        num_items = int(request.form.get('num_items', 1))
        tax_rate = float(request.form.get('tax_rate', 0))  # Get the tax rate from the form

        for i in range(num_items):
            product_name = request.form.get(f'product_name_{i}')
            product_price = float(request.form.get(f'product_price_{i}', 0))
            product_quantity = int(request.form.get(f'product_quantity_{i}', 0))

            if product_name and product_price and product_quantity:
                products.append({
                    'product_name': product_name,
                    'product_price': product_price,
                    'product_quantity': product_quantity,
                    'total': product_price * product_quantity
                })

        subtotal = sum(product['total'] for product in products)
        tax_amount = (subtotal * (tax_rate / 100))
        total_with_tax = subtotal + tax_amount

        author = request.form.get('author')  # Get the author's name from the form

        if 'generate_pdf' in request.form:
            pdf = generate_invoice_pdf(products, subtotal, tax_amount, total_with_tax, tax_rate, author)
            return Response(pdf, content_type='application/pdf')

    return render_template('invoice.html', num_items=num_items, products=products, subtotal=subtotal,
                           tax_amount=tax_amount, total_with_tax=total_with_tax, author=author)

def generate_invoice_pdf(products, subtotal, tax_amount, total_with_tax, tax_rate, author):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []

    styles = getSampleStyleSheet()

    title_style = styles['Title']
    content_style = styles['Normal']
    bold_style = styles['Heading1']

    title = "<b>Invoice Statement</b>"
    title_paragraph = Paragraph(title, title_style)
    story.append(title_paragraph)

    # Change the logo URL to the local file path
    logo_path = 'static/LimaSportingGoods.jpg'  # Update with the correct path to your locally saved image
    logo = Image(logo_path, width=80, height=80, hAlign='CENTER')
    story.append(logo)

    # Add Fax, Phone, Phone text lines
    contact_info = [
        ("Fax:", "419-222-8885"),
        ("Phone:", "419-222-1036"),
        ("Phone:", "419-228-7563")
    ]
    for label, text in contact_info:
        contact_paragraph = Paragraph(f"<b>{label}</b> {text}", content_style)
        contact_paragraph.alignment = 1  # Center alignment
        story.append(Spacer(1, 8))
        story.append(contact_paragraph)

    spacer = Spacer(1, 10)  # Add a small spacer
    story.append(spacer)

    data = [
        ["Description", "Unit Price", "Quantity", "Total"]
    ]

    for product in products:
        data.append([product['product_name'], "${:.2f}".format(product['product_price']),
                     str(product['product_quantity']), "${:.2f}".format(product['total'])])

    table = Table(data, colWidths=[300, 100, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)

    total_table_data = [
        [Paragraph("Subtotal:", content_style), Paragraph("${:.2f}".format(subtotal), content_style)],
        [Paragraph("Tax Amount ({}%):".format(tax_rate), content_style), Paragraph("${:.2f}".format(tax_amount), content_style)],
        [Paragraph("Total with Tax:", content_style), Paragraph("${:.2f}".format(total_with_tax), content_style)]
    ]
    total_table = Table(total_table_data, colWidths=[370, 90])
    total_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(total_table)

    # Add author information centered under the table
    author_paragraph = Paragraph(f"<b>By:</b> {author}", content_style)
    author_paragraph.alignment = 1  # Center alignment
    story.append(Spacer(1, 8))
    story.append(author_paragraph)

    # Add Buyer's Signature area at the bottom of the page
    signature_paragraph = Paragraph("<b>Buyer's Signature:</b>", content_style)
    signature_line = LongLine(200, 1, colors.black)  # Adjust line length as needed
    story.append(Spacer(1, 8))
    story.append(signature_paragraph)
    story.append(Spacer(1, 30))  # Add spacing between text and signature line
    story.append(signature_line)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)  # Use a different port, e.g., 8000
