#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用入口点，用于启动Flask应用
"""

import os
import sys

# 将当前目录添加到sys.path中，确保能正确导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import create_app

if __name__ == "__main__":
    from app.main import main
    app = create_app()
    main(app)