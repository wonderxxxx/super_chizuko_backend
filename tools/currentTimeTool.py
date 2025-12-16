import datetime

class CurrentTimeTool:
    """获取当前时间工具"""
    
    def getCurrentTime(self):
        """获取当前时间"""
        # 格式化当前时间
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {"currentTime": current_time}
