"""
数据库连接管理器
负责数据库连接池管理、连接获取、事务处理等

🚀 V2.0 升级：自动检测并使用连接池，向后兼容
"""
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import logging
from typing import Optional, Dict, Any
import time
import threading

logger = logging.getLogger(__name__)

# 🎯 尝试导入连接池库
try:
    from dbutils.pooled_db import PooledDB
    POOL_AVAILABLE = True
    logger.info("🚀 检测到DBUtils，启用连接池模式")
except ImportError:
    POOL_AVAILABLE = False
    logger.info("📎 DBUtils未安装，使用单连接模式")

class DatabaseManager:
    """数据库连接管理器（支持自动连接池）"""
    
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'port': 13306,  # Docker映射的端口
            'user': 'root',
            'password': '123456',
            'database': 'e2b_server_data',
            'charset': 'utf8mb4',
            'use_unicode': True,  # 启用Unicode支持
            'cursorclass': DictCursor,
            'autocommit': False,  # 手动控制事务
            'connect_timeout': 15,  # 🔧 优化：增加连接超时
            'read_timeout': 45,     # 🔧 优化：增加读取超时
            'write_timeout': 45,    # 🔧 优化：增加写入超时
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"  # 设置SQL模式
        }
        
        # 🎯 智能初始化：优先使用连接池
        self.use_pool = POOL_AVAILABLE
        self._connection = None
        self._pool = None
        self._stats = {'total_requests': 0, 'failed_requests': 0}
        self._lock = threading.Lock()
        
        if self.use_pool:
            self._init_connection_pool()
        else:
            logger.warning("⚠️ 降级到单连接模式，建议安装DBUtils以获得更好性能")
    
    def _init_connection_pool(self):
        """初始化数据库连接池"""
        try:
            logger.info("🚀 正在初始化数据库连接池...")
            
            # 🎯 连接池配置
            pool_config = {
                'creator': pymysql,
                'maxconnections': 20,    # 最大连接数
                'mincached': 5,          # 最少保持连接数  
                'maxcached': 10,         # 最多闲置连接数
                'maxshared': 15,         # 最大共享连接数
                'blocking': True,        # 连接池满时等待
                'maxusage': 1000,        # 连接最大使用次数
                'setsession': [          # 连接初始化命令
                    'SET AUTOCOMMIT = 0',
                    'SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci',
                    'SET CHARACTER SET utf8mb4',
                    'SET SESSION character_set_client = utf8mb4',
                    'SET SESSION character_set_connection = utf8mb4',
                    'SET SESSION character_set_results = utf8mb4',
                    'SET SESSION collation_connection = utf8mb4_unicode_ci',
                    "SET sql_mode='STRICT_TRANS_TABLES'"
                ],
                'ping': 4,  # 最严格的连接检查
                **self.db_config
            }
            
            self._pool = PooledDB(**pool_config)
            
            # 测试连接池
            conn = self._pool.connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
            conn.close()
            
            logger.info(f"✅ 连接池初始化成功！测试结果: {result}")
            
        except Exception as e:
            logger.error(f"❌ 连接池初始化失败，降级到单连接模式: {e}")
            self.use_pool = False
            self._pool = None
    
    def get_connection(self):
        """获取数据库连接，智能选择连接池或单连接模式"""
        with self._lock:
            self._stats['total_requests'] += 1
            
        if self.use_pool and self._pool:
            # 🚀 连接池模式
            try:
                logger.debug("📋 从连接池获取连接...")
                return self._pool.connection()
            except Exception as e:
                logger.error(f"❌ 连接池获取连接失败: {e}")
                self._stats['failed_requests'] += 1
                # 降级到单连接模式
                return self._get_single_connection()
        else:
            # 📎 单连接模式（降级或原始模式）
            return self._get_single_connection()
    
    def _get_single_connection(self):
        """单连接模式的连接获取（原始逻辑）"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if self._connection is None or not self._connection.open:
                    logger.info("创建新的数据库连接...")
                    self._connection = pymysql.connect(**self.db_config)
                    
                    # 彻底设置连接字符集
                    with self._connection.cursor() as cursor:
                        cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
                        cursor.execute("SET CHARACTER SET utf8mb4")
                        cursor.execute("SET character_set_client = utf8mb4")
                        cursor.execute("SET character_set_connection = utf8mb4") 
                        cursor.execute("SET character_set_results = utf8mb4")
                        cursor.execute("SET collation_connection = utf8mb4_unicode_ci")
                        # 确保会话级别字符集设置
                        cursor.execute("SET SESSION character_set_client = utf8mb4")
                        cursor.execute("SET SESSION character_set_connection = utf8mb4")
                        cursor.execute("SET SESSION character_set_results = utf8mb4")
                    
                    logger.info("数据库连接创建成功，字符集已彻底设置为utf8mb4")
                
                # 测试连接
                self._connection.ping(reconnect=True)
                return self._connection
                
            except Exception as e:
                retry_count += 1
                logger.error(f"数据库连接失败 (尝试 {retry_count}/{max_retries}): {e}")
                self._stats['failed_requests'] += 1
                
                if retry_count < max_retries:
                    time.sleep(1)  # 等待1秒后重试
                else:
                    raise Exception(f"数据库连接失败，已尝试 {max_retries} 次: {e}")
    
    @contextmanager
    def get_cursor(self):
        """获取游标的上下文管理器"""
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    @contextmanager 
    def transaction(self):
        """事务上下文管理器"""
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            # 开始事务
            connection.begin()
            logger.debug("开始数据库事务")
            yield cursor
            # 提交事务
            connection.commit()
            logger.debug("事务提交成功")
        except Exception as e:
            # 回滚事务
            connection.rollback()
            logger.error(f"事务回滚: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_query(self, sql: str, params: Optional[tuple] = None) -> list:
        """执行查询语句"""
        with self.get_cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()
    
    def execute_insert(self, sql: str, params: Optional[tuple] = None) -> int:
        """执行插入语句，返回最后插入的ID"""
        with self.transaction() as cursor:
            cursor.execute(sql, params)
            return cursor.lastrowid
    
    def execute_batch_insert(self, sql: str, params_list: list) -> int:
        """批量插入，返回影响的行数"""
        with self.transaction() as cursor:
            affected_rows = cursor.executemany(sql, params_list)
            return affected_rows
    
    def close(self):
        """关闭数据库连接"""
        if self.use_pool and self._pool:
            # 连接池模式下，关闭整个池
            try:
                self._pool.close()
                logger.info("🔒 连接池已关闭")
            except Exception as e:
                logger.error(f"关闭连接池失败: {e}")
        elif self._connection and self._connection.open:
            # 单连接模式下，关闭单个连接
            self._connection.close()
            logger.info("📎 数据库连接已关闭")
    
    def get_stats(self):
        """获取连接管理器统计信息"""
        stats = {
            'mode': 'connection_pool' if self.use_pool else 'single_connection',
            'pool_available': POOL_AVAILABLE,
            'total_requests': self._stats['total_requests'],
            'failed_requests': self._stats['failed_requests'],
            'success_rate': 0
        }
        
        if stats['total_requests'] > 0:
            stats['success_rate'] = (stats['total_requests'] - stats['failed_requests']) / stats['total_requests']
        
        # 连接池专有统计
        if self.use_pool and self._pool:
            try:
                # DBUtils内部统计信息
                stats['pool_info'] = {
                    'max_connections': getattr(self._pool, '_maxconnections', 'unknown'),
                    'current_connections': len(getattr(self._pool, '_cache', [])),
                    'pool_type': 'PooledDB'
                }
            except Exception as e:
                stats['pool_info'] = {'error': str(e)}
        
        return stats
    
    def health_check(self):
        """健康检查"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1 as health_check")
                result = cursor.fetchone()
                
            return {
                'status': 'healthy',
                'mode': 'connection_pool' if self.use_pool else 'single_connection',
                'test_result': result,
                'pool_available': POOL_AVAILABLE
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'mode': 'connection_pool' if self.use_pool else 'single_connection'
            }

# 全局数据库管理器实例
db_manager = DatabaseManager()
