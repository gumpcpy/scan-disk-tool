from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QPushButton, QFileDialog, QCheckBox, QLineEdit,
                           QLabel, QTextEdit, QMenuBar, QMenu, QAction, QHBoxLayout,
                           QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, QLocale, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QIcon, QDesktopServices
import sys
import yaml
from pathlib import Path
from logic import HardDiskScanner
from enum import Enum
from datetime import datetime
import os

class Language(Enum):
    EN = "English"
    ZH_TW = "繁體中文"
    ZH_CN = "简体中文"

class ScanThread(QThread):
    """掃描線程類"""
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, scan_path, output_path, rules):
        super().__init__()
        self.scan_path = scan_path
        self.output_path = output_path
        self.rules = rules
        
    def run(self):
        try:
            # 創建掃描器實例
            scanner = HardDiskScanner(log_callback=self.log_signal.emit)
            
            # 執行掃描
            results = scanner.scan_directory(self.scan_path, self.rules)
            
            # 保存到CSV
            if results:
                scanner.save_to_csv(self.output_path)
                self.finished_signal.emit(results)
            else:
                self.log_signal.emit("未找到符合條件的文件")
                self.finished_signal.emit([])
                
        except Exception as e:
            self.error_signal.emit(str(e))

class HardDiskScannerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.load_config()
        
        # 根據系統語言設置默認語言
        system_locale = QLocale.system().name()
        if system_locale.startswith('zh'):
            if 'TW' in system_locale or 'HK' in system_locale:
                self.current_language = Language.ZH_TW
            else:
                self.current_language = Language.ZH_CN
        else:
            self.current_language = Language.EN
        
        self.scan_thread = None
        self.initUI()
        self.update_ui_text()
        self.update_all_styles()  # 初始化時設置樣式
        self.log("status_ready")

    def load_config(self):
        """載入配置文件"""
        config_path = Path(__file__).parent / 'config.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.translations = {
            Language.EN: self.config['translations']['en'],
            Language.ZH_TW: self.config['translations']['zh_tw'],
            Language.ZH_CN: self.config['translations']['zh_cn']
        }
        
        self.version = self.config['version']

    def initUI(self):
        # 創建中心小部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 創建菜單欄
        self.create_menu_bar()
        
        # 第一行：選擇要掃描的路徑
        scan_folder_layout = QHBoxLayout()
        scan_folder_label = QLabel(self)
        scan_folder_label.setMinimumWidth(100)
        self.scan_folder_label = scan_folder_label
        self.scan_folder_input = QLineEdit(self)
        self.scan_folder_input.setReadOnly(True)
        self.scan_folder_input.setPlaceholderText(self.translations[self.current_language]['select_folder_placeholder'])
        self.scan_folder_button = QPushButton(self)
        self.scan_folder_button.setStyleSheet(self.get_button_style())
        self.scan_folder_button.clicked.connect(self.select_scan_folder)
        scan_folder_layout.addWidget(scan_folder_label)
        scan_folder_layout.addWidget(self.scan_folder_input)
        scan_folder_layout.addWidget(self.scan_folder_button)
        layout.addLayout(scan_folder_layout)

        # 第二行：選擇CSV的儲存路徑
        csv_output_layout = QHBoxLayout()
        csv_output_label = QLabel(self)
        csv_output_label.setMinimumWidth(100)
        self.csv_output_label = csv_output_label
        self.csv_output_input = QLineEdit(self)
        self.csv_output_input.setReadOnly(True)
        self.csv_output_input.setPlaceholderText(self.translations[self.current_language]['select_output_placeholder'])
        self.csv_output_button = QPushButton(self)
        self.csv_output_button.setStyleSheet(self.get_button_style())
        self.csv_output_button.clicked.connect(self.select_csv_output)
        csv_output_layout.addWidget(csv_output_label)
        csv_output_layout.addWidget(self.csv_output_input)
        csv_output_layout.addWidget(self.csv_output_button)
        layout.addLayout(csv_output_layout)
        
        # 第三行～第五行：三個checkbox規則
        rules_label = QLabel(self)
        self.rules_label = rules_label
        layout.addWidget(rules_label)
        
        # RDC規則
        self.rdc_checkbox = QCheckBox(self)
        self.rdc_checkbox.setChecked(True)  # 預設checked
        layout.addWidget(self.rdc_checkbox)
        
        # 影像序列規則
        self.image_sequence_checkbox = QCheckBox(self)
        self.image_sequence_checkbox.setChecked(True)  # 預設checked
        layout.addWidget(self.image_sequence_checkbox)
        
        # MOV規則（可自定義擴展名）
        mov_layout = QHBoxLayout()
        self.mov_checkbox = QCheckBox(self)
        self.mov_checkbox.setChecked(True)  # 預設checked
        self.mov_checkbox.stateChanged.connect(self.on_mov_checkbox_changed)
        
        self.mov_extension_input = QLineEdit(self)
        self.mov_extension_input.setText(".mov")  # 預設值
        self.mov_extension_input.setMaximumWidth(80)
        self.mov_extension_input.setEnabled(True)  # 預設啟用
        self.mov_extension_input.setPlaceholderText(".mov")
        
        mov_layout.addWidget(self.mov_checkbox)
        mov_layout.addWidget(self.mov_extension_input)
        mov_layout.addStretch()  # 右側彈性空間
        layout.addLayout(mov_layout)
        
        # 第六行：開始按鈕
        self.start_button = QPushButton(self)
        self.start_button.setStyleSheet(self.get_start_button_style())
        self.start_button.clicked.connect(self.start_processing)
        layout.addWidget(self.start_button)

        # 日誌區域
        self.log_text = QTextEdit(self)
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.update_log_style()
        layout.addWidget(self.log_text)
        
        # 清空日誌按鈕（右對齊）
        clear_log_layout = QHBoxLayout()
        clear_log_layout.addStretch()  # 左側彈性空間
        self.clear_log_button = QPushButton(self)
        self.clear_log_button.setStyleSheet(self.get_clear_button_style())
        self.clear_log_button.clicked.connect(self.clear_log)
        clear_log_layout.addWidget(self.clear_log_button)
        layout.addLayout(clear_log_layout)
        
        # 添加底部信息欄
        bottom_info = QHBoxLayout()
        
        # 左側空白區域
        left_spacer = QLabel("")
        left_spacer.setStyleSheet(self.get_bottom_label_style())
        bottom_info.addWidget(left_spacer)
        
        # 版權信息（中間對齊）
        copyright_label = QLabel(self)
        copyright_label.setStyleSheet(self.get_bottom_label_style())
        copyright_label.setAlignment(Qt.AlignCenter)
        bottom_info.addWidget(copyright_label)
        self.copyright_label = copyright_label
        
        # 版本信息（右對齊）- 可點擊的鏈接
        version_label = QLabel(self)
        version_label.setStyleSheet(self.get_hyperlink_style())
        version_label.setAlignment(Qt.AlignRight)
        version_label.setOpenExternalLinks(True)
        version_label.linkActivated.connect(self.open_github_link)
        bottom_info.addWidget(version_label)
        self.version_label = version_label
        
        layout.addLayout(bottom_info)

        self.setGeometry(300, 300, 700, 500)
        self.setWindowTitle(self.translations[self.current_language]['window_title'])

    def get_button_style(self):
        """獲取按鈕樣式"""
        if self.is_dark_theme():
            return """
                QPushButton {
                    background-color: #4a4a4a;
                    border: 1px solid #666666;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                }
                QPushButton:pressed {
                    background-color: #3a3a3a;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #90EE90;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: black;
                }
                QPushButton:hover {
                    background-color: #98FB98;
                }
                QPushButton:pressed {
                    background-color: #7ED87E;
                }
            """

    def get_start_button_style(self):
        """獲取開始按鈕樣式"""
        if self.is_dark_theme():
            return """
                QPushButton {
                    background-color: #0078d4; 
                    border: 1px solid #106ebe;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    color: #ffffff;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
                QPushButton:disabled {
                    background-color: #3a3a3a;
                    color: #666666;
                    border: 1px solid #555555;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: lightblue; 
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    color: black;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #87CEEB;
                }
                QPushButton:pressed {
                    background-color: #add8e6;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
            """

    def get_clear_button_style(self):
        """獲取清空按鈕樣式"""
        if self.is_dark_theme():
            return """
                QPushButton {
                    background-color: #d13438;
                    border: 1px solid #a52a2a;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: #e74c3c;
                }
                QPushButton:pressed {
                    background-color: #c0392b;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #ffcccc;
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 4px 8px;
                    color: black;
                }
                QPushButton:hover {
                    background-color: #ffaaaa;
                }
                QPushButton:pressed {
                    background-color: #ff9999;
                }
            """

    def get_bottom_label_style(self):
        """獲取底部標籤樣式"""
        if self.is_dark_theme():
            return "color: #cccccc;"
        else:
            return "color: gray;"

    def get_hyperlink_style(self):
        """獲取超鏈接樣式"""
        if self.is_dark_theme():
            return """
                QLabel {
                    color: #4A9EFF;
                    text-decoration: underline;
                }
                QLabel:hover {
                    color: #6BB6FF;
                }
            """
        else:
            return """
                QLabel {
                    color: #0066CC;
                    text-decoration: underline;
                }
                QLabel:hover {
                    color: #0080FF;
                }
            """

    def on_mov_checkbox_changed(self, state):
        """MOV checkbox狀態變化處理"""
        is_checked = state == Qt.Checked
        self.mov_extension_input.setEnabled(is_checked)

    def open_github_link(self, url):
        """打開GitHub鏈接"""
        QDesktopServices.openUrl(QUrl(url))

    def is_dark_theme(self):
        """檢測是否為深色主題"""
        # 獲取應用程序的調色板
        palette = self.palette()
        # 檢查窗口背景色是否較暗
        window_color = palette.color(palette.Window)
        # 如果亮度值小於128，則認為是深色主題
        return window_color.lightness() < 128

    def update_log_style(self):
        """根據系統主題更新日誌視窗樣式"""
        if self.is_dark_theme():
            # 深色主題樣式
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #2b2b2b;
                    color: #ffffff;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 5px;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                }
                QTextEdit:focus {
                    border: 1px solid #0078d4;
                }
            """)
        else:
            # 淺色主題樣式
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 5px;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                }
                QTextEdit:focus {
                    border: 1px solid #0078d4;
                }
            """)

    def update_all_styles(self):
        """更新所有UI組件的樣式"""
        # 更新按鈕樣式
        self.scan_folder_button.setStyleSheet(self.get_button_style())
        self.csv_output_button.setStyleSheet(self.get_button_style())
        self.start_button.setStyleSheet(self.get_start_button_style())
        self.clear_log_button.setStyleSheet(self.get_clear_button_style())
        
        # 更新底部標籤樣式
        self.copyright_label.setStyleSheet(self.get_bottom_label_style())
        self.version_label.setStyleSheet(self.get_hyperlink_style())
        
        # 更新日誌樣式
        self.update_log_style()

    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # 幫助菜單
        help_menu = menubar.addMenu('')  # 文字會在update_ui_text中更新
        self.help_menu = help_menu
        
        # 用法介紹
        info_action = QAction('', self)
        info_action.triggered.connect(self.show_info)
        help_menu.addAction(info_action)
        self.info_action = info_action
        
        # 關於
        about_action = QAction('', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        self.about_action = about_action
        
        # 語言菜單
        language_menu = menubar.addMenu('')
        self.language_menu = language_menu
        
        # 添加語言選項
        for lang in Language:
            action = QAction(lang.value, self)
            action.setData(lang)
            action.triggered.connect(self.change_language)
            language_menu.addAction(action)

    def update_ui_text(self):
        """更新界面文字"""
        texts = self.translations[self.current_language]
        
        self.setWindowTitle(texts['window_title'])
        self.scan_folder_label.setText(texts['select_scan_folder'])
        self.csv_output_label.setText(texts['select_csv_output'])
        self.rules_label.setText(texts['scan_rules'])
        self.rdc_checkbox.setText(texts['rule_rdc'])
        self.image_sequence_checkbox.setText(texts['rule_image_sequence'])
        self.mov_checkbox.setText(texts['rule_mov'])
        self.start_button.setText(texts['start_processing'])
        self.clear_log_button.setText(texts['clear_log'])
        
        # 更新佔位符文字
        self.scan_folder_input.setPlaceholderText(texts['select_folder_placeholder'])
        self.csv_output_input.setPlaceholderText(texts['select_output_placeholder'])
        
        # 更新菜單文字
        self.help_menu.setTitle(texts['menu_help'])
        self.info_action.setText(texts['menu_usage'])
        self.about_action.setText(texts['menu_about'])
        self.language_menu.setTitle(texts['language'])
        
        # 更新底部信息
        self.copyright_label.setText(texts['copyright'])
        self.version_label.setText(texts['version_text'].format(self.version)) 
        
        self.scan_folder_button.setText(texts['browse_button'])
        self.csv_output_button.setText(texts['browse_button'])

    def log(self, message_key, *args):
        """添加日誌消息到日誌區域"""
        text = self.translations[self.current_language].get(message_key, message_key)
        if args:
            text = text.format(*args)
        
        # 添加時間戳
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {text}")

    def clear_log(self):
        """清空日誌"""
        self.log_text.clear()

    def change_language(self):
        """切換語言"""
        action = self.sender()
        self.current_language = action.data()
        self.update_ui_text()
        self.update_all_styles()  # 更新所有樣式
        self.log("status_ready")

    def show_info(self):
        """顯示使用說明"""
        texts = self.translations[self.current_language]
        usage_steps = self.config['usage_steps'][self.current_language.name.lower()]
        
        info_text = "\n".join(usage_steps)
        QMessageBox.information(self, texts['menu_usage'], info_text)

    def show_about(self):
        """顯示關於信息"""
        texts = self.translations[self.current_language]
        about_text = f"""
{texts['window_title']}
{texts['version_text'].format(self.version)}

{texts['copyright']}
        """
        QMessageBox.about(self, texts['menu_about'], about_text.strip())

    def select_scan_folder(self):
        """選擇掃描資料夾"""
        folder = QFileDialog.getExistingDirectory(self, self.translations[self.current_language]['select_scan_folder'])
        if folder:
            self.scan_folder_input.setStyleSheet("")  # 重置樣式
            self.scan_folder_input.setText(folder)
            self.log("log_scanning", folder)

    def select_csv_output(self):
        """選擇CSV輸出位置"""
        # 生成默認文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"scan_results_{timestamp}.csv"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            self.translations[self.current_language]['select_csv_output'],
            default_filename,
            "CSV files (*.csv)"
        )
        if file_path:
            self.csv_output_input.setStyleSheet("")  # 重置樣式
            self.csv_output_input.setText(file_path)
            self.log("log_scanning", file_path)

    def start_processing(self):
        """開始處理"""
        # 檢查輸入和輸出路徑
        scan_path = self.scan_folder_input.text()
        output_path = self.csv_output_input.text()
        
        # 檢查是否選擇了掃描路徑
        if not scan_path:
            self.scan_folder_input.setStyleSheet("color: red;")
            self.scan_folder_input.setText(self.translations[self.current_language]['error_no_scan_folder'])
            self.log("error_no_scan_folder")
            return
            
        # 檢查是否選擇了輸出路徑
        if not output_path:
            self.csv_output_input.setStyleSheet("color: red;")
            self.csv_output_input.setText(self.translations[self.current_language]['error_no_output_folder'])
            self.log("error_no_output_folder")
            return
            
        # 檢查是否至少選擇了一個規則
        rules = {
            'rdc': self.rdc_checkbox.isChecked(),
            'image_sequence': self.image_sequence_checkbox.isChecked(),
            'custom_extension': self.mov_checkbox.isChecked()
        }
        
        # 如果選擇了自定義擴展名規則，獲取擴展名
        if self.mov_checkbox.isChecked():
            extension = self.mov_extension_input.text().strip()
            if not extension:
                extension = ".mov"  # 預設值
            rules['custom_extension'] = extension
        
        if not any(rules.values()):
            self.log("error_no_rules")
            return
        
        # 禁用開始按鈕
        self.start_button.setEnabled(False)
        self.start_button.setText(self.translations[self.current_language]['processing'])
        
        self.log("status_processing")
        
        # 創建並啟動掃描線程
        self.scan_thread = ScanThread(scan_path, output_path, rules)
        self.scan_thread.log_signal.connect(self.log)
        self.scan_thread.finished_signal.connect(self.on_scan_finished)
        self.scan_thread.error_signal.connect(self.on_scan_error)
        self.scan_thread.start()

    def on_scan_finished(self, results):
        """掃描完成回調"""
        self.start_button.setEnabled(True)
        self.start_button.setText(self.translations[self.current_language]['start_processing'])
        
        if results:
            self.log("log_completed", len(results))
        else:
            self.log("log_completed", 0)
        
        self.log("status_complete")

    def on_scan_error(self, error_message):
        """掃描錯誤回調"""
        self.start_button.setEnabled(True)
        self.start_button.setText(self.translations[self.current_language]['start_processing'])
        self.log("log_error", error_message)
        self.log("status_error", error_message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = HardDiskScannerApp()
    ex.show()
    sys.exit(app.exec_())
