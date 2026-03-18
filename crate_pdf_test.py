from reportlab.pdfgen import canvas

c = canvas.Canvas("data/papers/test.pdf")
c.drawString(100, 750, "This paper uses deep learning [1]")
c.drawString(100, 730, "[1] Deep learning is widely used in computer vision.")
c.save()