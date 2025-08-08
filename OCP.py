import sys
import subprocess
import pytesseract
import time
import os
import tempfile
from PIL import Image
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QFileDialog, QLabel
)
from PyQt5.QtGui import QGuiApplication, QPixmap
from PyQt5.QtCore import Qt, QTimer


pytesseract.pytesseract.tesseract_cmd = r"path to tesseract"


class OCRApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🧠 OCR Reader | English + Polish")
        self.setGeometry(300, 150, 700, 550)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas;
            }
            QPushButton {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #007acc;
                color: white;
            }
            QTextEdit {
                background-color: #252526;
                border: 1px solid #3e3e42;
                padding: 10px;
                font-size: 13px;
                color: #dcdcdc;
            }
            QLabel {
                font-size: 16px;
                padding: 10px 0;
            }
        """)

        layout = QVBoxLayout()

        self.label = QLabel("Choose an action:")
        layout.addWidget(self.label)

        self.import_btn = QPushButton("📁 Import Image from File")
        self.import_btn.clicked.connect(self.import_image)
        layout.addWidget(self.import_btn)

        self.capture_btn = QPushButton("✂️ Capture Region via Snip Tool")
        self.capture_btn.clicked.connect(self.capture_via_snip)
        layout.addWidget(self.capture_btn)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(False)
        layout.addWidget(self.output_text)

        self.setLayout(layout)


        self.clipboard_timer = QTimer()
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.initial_clipboard_content = None
        self.waiting_for_snip = False

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Escape and self.waiting_for_snip:

            self.clipboard_timer.stop()
            self.waiting_for_snip = False
            self.output_text.setText("[ℹ️] Snipping canceled by user (ESC pressed)")
            self.label.setText("Choose an action:")
            self.showNormal()
            self.activateWindow()
            self.raise_()
        else:
            super().keyPressEvent(event)

    def extract_text_from_image(self, image):
        try:

            text = pytesseract.image_to_string(image, lang="eng+pol")
            if text.strip():
                self.output_text.setText(text)
                return
        except Exception as e:

            if "pol" in str(e).lower() or "language" in str(e).lower():
                try:
                    text = pytesseract.image_to_string(image, lang="eng")
                    info_msg = "[ℹ️ INFO] Polish language not available, using English only.\n"
                    info_msg += "To add Polish support:\n"
                    info_msg += "1. Download: https://github.com/tesseract-ocr/tessdata/raw/main/pol.traineddata\n"
                    info_msg += f"2. Save to: {os.path.dirname(pytesseract.pytesseract.tesseract_cmd)}\\tessdata\\\n"
                    info_msg += "3. Restart this app\n\n"
                    info_msg += "=" * 50 + "\n\n" + text
                    self.output_text.setText(info_msg)
                    return
                except Exception as e2:
                    self.output_text.setText(f"[ERROR] Failed with English too: {e2}")
                    return


        try:
            text = pytesseract.image_to_string(image, lang="eng")
            self.output_text.setText(f"[ℹ️ Using English only]\n\n{text}")
        except Exception as e:
            self.output_text.setText(f"[ERROR] OCR failed: {e}")

    def import_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            image = Image.open(file_path)
            self.extract_text_from_image(image)

    def capture_via_snip(self):

        clipboard = QGuiApplication.clipboard()
        self.initial_clipboard_content = clipboard.image()


        self.showMinimized()
        self.waiting_for_snip = True


        clipboard.clear()


        try:
            subprocess.Popen("explorer ms-screenclip:", shell=True)
        except Exception as e:
            self.output_text.setText(f"[ERROR] Could not open Snip Tool: {e}")
            self.showNormal()
            self.activateWindow()
            self.raise_()
            return

        self.label.setText("✂️ Waiting for you to snip... (Press ESC to cancel, will timeout in 30s)")


        self.clipboard_timer.start(200)  # Check every 200ms


        QTimer.singleShot(30000, self.timeout_snip)  # 30 second timeout

    def check_clipboard(self):
        if not self.waiting_for_snip:
            return

        clipboard = QGuiApplication.clipboard()
        current_image = clipboard.image()


        if (not current_image.isNull() and
                current_image.size().width() > 0 and
                current_image.size().height() > 0 and
                not self.images_equal(current_image, self.initial_clipboard_content)):
            self.process_clipboard_image(current_image)

    def images_equal(self, img1, img2):

        if img1.isNull() and img2.isNull():
            return True
        if img1.isNull() or img2.isNull():
            return False
        if img1.size() != img2.size():
            return False


        try:
            ba1 = img1.bits().asstring(img1.byteCount())
            ba2 = img2.bits().asstring(img2.byteCount())
            return ba1 == ba2
        except:
            return False

    def process_clipboard_image(self, qimage):

        self.clipboard_timer.stop()
        self.waiting_for_snip = False
        temp_file = None

        try:

            import uuid
            temp_filename = f"snip_temp_{uuid.uuid4().hex[:8]}.png"
            temp_file = os.path.join(tempfile.gettempdir(), temp_filename)


            qpixmap = QPixmap.fromImage(qimage)
            if not qpixmap.save(temp_file, "PNG"):
                raise Exception("Failed to save clipboard image to temp file")


            if not os.path.exists(temp_file) or os.path.getsize(temp_file) == 0:
                raise Exception("Temp file was not created properly")


            with Image.open(temp_file) as pil_image:

                if pil_image.mode not in ('RGB', 'L'):
                    pil_image = pil_image.convert('RGB')
                self.extract_text_from_image(pil_image)

            self.label.setText("✅ OCR completed! Choose an action:")

        except Exception as e:
            self.output_text.setText(f"[ERROR] Failed to process clipboard image: {e}")
            self.label.setText("❌ Failed to process image. Choose an action:")

        finally:

            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"✅ Cleaned up temp file: {temp_file}")
                except Exception as cleanup_error:
                    print(f"⚠️ Could not remove temp file {temp_file}: {cleanup_error}")

       
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def timeout_snip(self):

        if self.waiting_for_snip:
            self.clipboard_timer.stop()
            self.waiting_for_snip = False
            self.output_text.setText("[❗] Timeout: No new image found in clipboard. Did you cancel the snip?")
            self.label.setText("Choose an action:")
           
            self.showNormal()
            self.activateWindow()
            self.raise_()

    def closeEvent(self, event):

        if self.clipboard_timer.isActive():
            self.clipboard_timer.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ocr_app = OCRApp()
    ocr_app.show()
    sys.exit(app.exec_())
