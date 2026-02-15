"""
Data exporters for various formats
"""

import json
import csv
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

import structlog

logger = structlog.get_logger()


class BaseExporter(ABC):
    """Base class for data exporters"""
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def export(self, data: List[Dict[str, Any]], **kwargs) -> str:
        """Export data and return filepath"""
        pass
    
    @abstractmethod
    def append(self, data: List[Dict[str, Any]], **kwargs):
        """Append data to existing file"""
        pass


class JSONExporter(BaseExporter):
    """Export to JSON format"""
    
    def export(self, data: List[Dict[str, Any]], indent: int = 2, 
               ensure_ascii: bool = False, **kwargs) -> str:
        """
        Export data to JSON file
        
        Args:
            data: List of dictionaries to export
            indent: JSON indentation
            ensure_ascii: Whether to escape non-ASCII characters
        """
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii, 
                     default=str, **kwargs)
        
        logger.info("Exported JSON", filepath=self.filepath, records=len(data))
        return str(self.filepath)
    
    def append(self, data: List[Dict[str, Any]], **kwargs):
        """Append to JSON file (loads, appends, re-saves)"""
        existing = []
        if self.filepath.exists():
            with open(self.filepath, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        
        existing.extend(data)
        self.export(existing, **kwargs)
    
    def export_jsonl(self, data: List[Dict[str, Any]], **kwargs) -> str:
        """Export to JSON Lines format"""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False, default=str) + '\n')
        
        logger.info("Exported JSONL", filepath=self.filepath, records=len(data))
        return str(self.filepath)


class CSVExporter(BaseExporter):
    """Export to CSV format"""
    
    def export(self, data: List[Dict[str, Any]], delimiter: str = ',',
               encoding: str = 'utf-8', **kwargs) -> str:
        """
        Export data to CSV file
        
        Args:
            data: List of dictionaries to export
            delimiter: CSV delimiter character
            encoding: File encoding
        """
        if not data:
            logger.warning("No data to export")
            return str(self.filepath)
        
        fieldnames = list(data[0].keys())
        
        with open(self.filepath, 'w', newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info("Exported CSV", filepath=self.filepath, records=len(data))
        return str(self.filepath)
    
    def append(self, data: List[Dict[str, Any]], delimiter: str = ',',
               encoding: str = 'utf-8', **kwargs):
        """Append to CSV file"""
        if not data:
            return
        
        fieldnames = list(data[0].keys())
        mode = 'a' if self.filepath.exists() else 'w'
        
        with open(self.filepath, mode, newline='', encoding=encoding) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
            if mode == 'w':
                writer.writeheader()
            writer.writerows(data)
        
        logger.info("Appended to CSV", filepath=self.filepath, records=len(data))
    
    def export_tsv(self, data: List[Dict[str, Any]], **kwargs) -> str:
        """Export as TSV (tab-separated)"""
        return self.export(data, delimiter='\t', **kwargs)


class ExcelExporter(BaseExporter):
    """Export to Excel format"""
    
    def export(self, data: List[Dict[str, Any]], sheet_name: str = 'Sheet1',
               engine: str = 'openpyxl', **kwargs) -> str:
        """
        Export data to Excel file
        
        Args:
            data: List of dictionaries to export
            sheet_name: Name of the worksheet
            engine: Excel engine ('openpyxl' or 'xlsxwriter')
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Excel export. Install with: pip install pandas")
        
        df = pd.DataFrame(data)
        
        # Determine engine from file extension
        if self.filepath.suffix == '.xlsx':
            engine = 'openpyxl'
        elif self.filepath.suffix == '.xls':
            engine = 'xlwt'
        
        df.to_excel(self.filepath, sheet_name=sheet_name, engine=engine, 
                   index=False, **kwargs)
        
        logger.info("Exported Excel", filepath=self.filepath, records=len(data))
        return str(self.filepath)
    
    def export_multiple_sheets(self, data_dict: Dict[str, List[Dict]], 
                               **kwargs) -> str:
        """
        Export multiple sheets to single Excel file
        
        Args:
            data_dict: Dict of sheet_name -> data
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for Excel export")
        
        with pd.ExcelWriter(self.filepath, engine='openpyxl') as writer:
            for sheet_name, data in data_dict.items():
                df = pd.DataFrame(data)
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info("Exported multi-sheet Excel", filepath=self.filepath, 
                   sheets=len(data_dict))
        return str(self.filepath)
    
    def append(self, data: List[Dict[str, Any]], **kwargs):
        """Append is not efficiently supported for Excel"""
        raise NotImplementedError("Excel append not supported. Use export instead.")


class SQLiteExporter(BaseExporter):
    """Export to SQLite database"""
    
    def export(self, data: List[Dict[str, Any]], table_name: str = 'scraped_data',
               if_exists: str = 'replace', **kwargs) -> str:
        """
        Export data to SQLite database
        
        Args:
            data: List of dictionaries to export
            table_name: Name of the table
            if_exists: Behavior if table exists ('fail', 'replace', 'append')
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for SQLite export")
        
        df = pd.DataFrame(data)
        
        from sqlalchemy import create_engine
        engine = create_engine(f'sqlite:///{self.filepath}')
        
        df.to_sql(table_name, engine, if_exists=if_exists, index=False, **kwargs)
        
        logger.info("Exported to SQLite", filepath=self.filepath, 
                   table=table_name, records=len(data))
        return str(self.filepath)
    
    def append(self, data: List[Dict[str, Any]], table_name: str = 'scraped_data', 
               **kwargs):
        """Append to SQLite table"""
        self.export(data, table_name=table_name, if_exists='append', **kwargs)


class ParquetExporter(BaseExporter):
    """Export to Apache Parquet format"""
    
    def export(self, data: List[Dict[str, Any]], compression: str = 'snappy',
               **kwargs) -> str:
        """
        Export data to Parquet file
        
        Args:
            data: List of dictionaries to export
            compression: Compression algorithm ('snappy', 'gzip', 'brotli', 'none')
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas and pyarrow are required for Parquet export")
        
        df = pd.DataFrame(data)
        df.to_parquet(self.filepath, compression=compression, **kwargs)
        
        logger.info("Exported Parquet", filepath=self.filepath, records=len(data))
        return str(self.filepath)
    
    def append(self, data: List[Dict[str, Any]], **kwargs):
        """Append is not natively supported in Parquet"""
        raise NotImplementedError("Parquet append not supported. Use export instead.")


class MongoExporter:
    """Export to MongoDB"""
    
    def __init__(self, connection_string: str, database: str):
        try:
            from pymongo import MongoClient
        except ImportError:
            raise ImportError("pymongo is required for MongoDB export")
        
        self.client = MongoClient(connection_string)
        self.db = self.client[database]
    
    def export(self, data: List[Dict[str, Any]], collection_name: str,
               **kwargs) -> int:
        """
        Insert data into MongoDB collection
        
        Returns:
            Number of inserted documents
        """
        collection = self.db[collection_name]
        
        if len(data) == 1:
            result = collection.insert_one(data[0])
            inserted = 1 if result.inserted_id else 0
        else:
            result = collection.insert_many(data)
            inserted = len(result.inserted_ids)
        
        logger.info("Exported to MongoDB", collection=collection_name, 
                   records=inserted)
        return inserted
    
    def append(self, data: List[Dict[str, Any]], collection_name: str, **kwargs):
        """Alias for export (MongoDB handles duplicates via _id)"""
        return self.export(data, collection_name, **kwargs)
    
    def update_one(self, filter_dict: Dict, update_dict: Dict, 
                   collection_name: str, upsert: bool = True):
        """Update single document"""
        collection = self.db[collection_name]
        result = collection.update_one(filter_dict, {'$set': update_dict}, 
                                      upsert=upsert)
        return result.modified_count
    
    def close(self):
        """Close MongoDB connection"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


def auto_export(data: List[Dict[str, Any]], filepath: str, **kwargs) -> str:
    """
    Automatically select exporter based on file extension
    
    Args:
        data: Data to export
        filepath: Output file path
        **kwargs: Additional exporter options
        
    Returns:
        Path to exported file
    """
    path = Path(filepath)
    extension = path.suffix.lower()
    
    exporters = {
        '.json': JSONExporter,
        '.csv': CSVExporter,
        '.tsv': lambda p: CSVExporter(p),  # Will use tab delimiter
        '.xlsx': ExcelExporter,
        '.xls': ExcelExporter,
        '.parquet': ParquetExporter,
        '.db': SQLiteExporter,
        '.sqlite': SQLiteExporter,
    }
    
    if extension not in exporters:
        raise ValueError(f"Unsupported file extension: {extension}. "
                        f"Supported: {list(exporters.keys())}")
    
    exporter = exporters[extension](filepath)
    
    # Handle TSV special case
    if extension == '.tsv':
        return exporter.export(data, delimiter='\t', **kwargs)
    
    return exporter.export(data, **kwargs)
