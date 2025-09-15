import os
import csv
import re
from pathlib import Path
from typing import List, Tuple, Callable, Optional
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScanResult:
    """掃描結果類"""
    def __init__(self, raw: str, path: str, rule_type: str):
        self.raw = raw
        self.path = path
        self.rule_type = rule_type

class HardDiskScanner:
    """硬碟掃描器主類"""
    
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        """
        初始化掃描器
        
        Args:
            log_callback: 日誌回調函數，用於實時顯示掃描進度
        """
        self.log_callback = log_callback
        self.results: List[ScanResult] = []
        
        # 影像序列的常見擴展名
        self.image_extensions = {
            '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.gif', 
            '.exr', '.dpx', '.cin', '.r3d', '.ari', '.arri', '.mxf'
        }
        
        # 影像序列的命名模式（例如：IMG_001.jpg, IMG_002.jpg）
        self.sequence_patterns = [
            r'(.+?)_(\d{3,})\.',  # 文件名_數字.擴展名
            r'(.+?)(\d{3,})\.',   # 文件名數字.擴展名
            r'(.+?)_(\d{4,})\.',  # 文件名_四位數字.擴展名
        ]

    def log(self, message: str):
        """記錄日誌"""
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)

    def is_image_sequence(self, file_path: Path) -> bool:
        """
        檢查是否為影像序列
        
        Args:
            file_path: 文件路徑
            
        Returns:
            bool: 是否為影像序列
        """
        if not file_path.is_file():
            return False
            
        file_ext = file_path.suffix.lower()
        if file_ext not in self.image_extensions:
            return False
            
        # 獲取父目錄中的所有文件
        parent_dir = file_path.parent
        if not parent_dir.exists():
            return False
            
        # 獲取同目錄下的所有影像文件
        image_files = []
        for ext in self.image_extensions:
            image_files.extend(parent_dir.glob(f'*{ext}'))
            image_files.extend(parent_dir.glob(f'*{ext.upper()}'))
        
        if len(image_files) < 2:  # 至少需要2個文件才算序列
            return False
            
        # 檢查是否有符合序列命名模式的文件
        for pattern in self.sequence_patterns:
            matches = []
            for img_file in image_files:
                match = re.search(pattern, img_file.name, re.IGNORECASE)
                if match:
                    base_name = match.group(1)
                    matches.append((base_name, img_file))
            
            # 如果找到至少2個相同基礎名稱的文件，則認為是序列
            if len(matches) >= 2:
                # 檢查基礎名稱是否相同
                base_names = set(match[0] for match in matches)
                if len(base_names) == 1:  # 所有文件都有相同基礎名稱
                    return True
                    
        return False

    def scan_for_rdc(self, root_path: Path) -> List[ScanResult]:
        """
        掃描.RDC文件
        
        Args:
            root_path: 根路徑
            
        Returns:
            List[ScanResult]: 掃描結果列表
        """
        results = []
        self.log(f"開始掃描RDC文件: {root_path}")
        
        for file_path in root_path.rglob('*.RDC'):
            if file_path.is_file():
                # 獲取.RDC之前的字串作為RAW
                raw_name = file_path.stem  # 不包含擴展名的文件名
                result = ScanResult(
                    raw=raw_name,
                    path=str(file_path.parent),
                    rule_type="RDC"
                )
                results.append(result)
                self.log(f"找到RDC文件: {file_path}")
                
        return results

    def scan_for_image_sequence(self, root_path: Path) -> List[ScanResult]:
        """
        掃描影像序列
        
        Args:
            root_path: 根路徑
            
        Returns:
            List[ScanResult]: 掃描結果列表
        """
        results = []
        self.log(f"開始掃描影像序列: {root_path}")
        
        processed_dirs = set()  # 避免重複處理同一個目錄
        
        for file_path in root_path.rglob('*'):
            if file_path.is_file() and file_path.parent not in processed_dirs:
                if self.is_image_sequence(file_path):
                    # RAW為影像序列上一級的名稱
                    parent_dir = file_path.parent
                    raw_name = parent_dir.name
                    result = ScanResult(
                        raw=raw_name,
                        path=str(parent_dir),
                        rule_type="Image Sequence"
                    )
                    results.append(result)
                    self.log(f"找到影像序列: {parent_dir}")
                    processed_dirs.add(parent_dir)
                    
        return results

    def scan_for_custom_extension(self, root_path: Path, extension: str) -> List[ScanResult]:
        """
        掃描指定擴展名的文件（不分大小寫）
        
        Args:
            root_path: 根路徑
            extension: 文件擴展名（如 .mov, .mxf）
            
        Returns:
            List[ScanResult]: 掃描結果列表
        """
        results = []
        # 確保擴展名以點開頭
        if not extension.startswith('.'):
            extension = '.' + extension
        
        self.log(f"開始掃描{extension.upper()}文件: {root_path}")
        
        # 使用不區分大小寫的搜索
        for file_path in root_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() == extension.lower():
                # 獲取擴展名之前的字串作為RAW
                raw_name = file_path.stem  # 不包含擴展名的文件名
                result = ScanResult(
                    raw=raw_name,
                    path=str(file_path.parent),
                    rule_type=f"Custom Extension ({extension.upper()})"
                )
                results.append(result)
                self.log(f"找到{extension.upper()}文件: {file_path}")
                
        return results

    def scan_directory(self, root_path: str, rules: dict) -> List[ScanResult]:
        """
        掃描目錄
        
        Args:
            root_path: 根路徑
            rules: 掃描規則字典，包含 'rdc', 'image_sequence', 'custom_extension' 鍵
                  其中 'custom_extension' 的值為擴展名字符串（如 '.mov', '.mxf'）
            
        Returns:
            List[ScanResult]: 掃描結果列表
        """
        self.results = []
        root_path = Path(root_path)
        
        if not root_path.exists():
            raise ValueError(f"路徑不存在: {root_path}")
            
        self.log(f"開始掃描目錄: {root_path}")
        
        # 根據規則進行掃描
        if rules.get('rdc', False):
            rdc_results = self.scan_for_rdc(root_path)
            self.results.extend(rdc_results)
            
        if rules.get('image_sequence', False):
            image_results = self.scan_for_image_sequence(root_path)
            self.results.extend(image_results)
            
        if rules.get('custom_extension', False):
            extension = rules.get('custom_extension', '.mov')
            custom_results = self.scan_for_custom_extension(root_path, extension)
            self.results.extend(custom_results)
            
        self.log(f"掃描完成，共找到 {len(self.results)} 個項目")
        return self.results

    def save_to_csv(self, output_path: str) -> str:
        """
        將掃描結果保存到CSV文件
        
        Args:
            output_path: 輸出文件路徑
            
        Returns:
            str: 保存的文件路徑
        """
        if not self.results:
            raise ValueError("沒有掃描結果可保存")
            
        # 確保輸出目錄存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # 寫入表頭
            writer.writerow(['raw', 'path'])
            
            # 寫入數據
            for result in self.results:
                writer.writerow([result.raw, result.path])
                
        self.log(f"結果已保存到: {output_path}")
        return str(output_path)

    def get_results_summary(self) -> dict:
        """
        獲取掃描結果摘要
        
        Returns:
            dict: 結果摘要
        """
        summary = {
            'total': len(self.results),
            'by_rule': {}
        }
        
        for result in self.results:
            rule_type = result.rule_type
            if rule_type not in summary['by_rule']:
                summary['by_rule'][rule_type] = 0
            summary['by_rule'][rule_type] += 1
            
        return summary


def main():
    """測試函數"""
    # 創建掃描器實例
    def log_callback(message):
        print(f"[LOG] {message}")
    
    scanner = HardDiskScanner(log_callback=log_callback)
    
    # 測試掃描
    test_path = "/Users/gump/Documents/_Proj/qt_scan_disk"  # 使用當前目錄作為測試
    
    rules = {
        'rdc': True,
        'image_sequence': True,
        'mov': True
    }
    
    try:
        results = scanner.scan_directory(test_path, rules)
        print(f"掃描完成，找到 {len(results)} 個項目")
        
        # 顯示結果摘要
        summary = scanner.get_results_summary()
        print("結果摘要:")
        for rule_type, count in summary['by_rule'].items():
            print(f"  {rule_type}: {count}")
            
        # 保存到CSV
        if results:
            output_path = "/Users/gump/Desktop/scan_results.csv"
            scanner.save_to_csv(output_path)
            print(f"結果已保存到: {output_path}")
            
    except Exception as e:
        print(f"掃描過程中發生錯誤: {e}")


if __name__ == "__main__":
    main()
