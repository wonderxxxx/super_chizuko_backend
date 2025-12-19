import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import Config
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    """邮件发送服务"""

    def _create_email_content(self, email, verification_code):
        """生成符合智子角色设定的邮件内容（兄妹契约风格）"""

        # HTML 邮件内容
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>智子验证 - 兄妹契约</title>
            <style>
                body {{
                    background: linear-gradient(135deg, #2D1B69 0%, #0F0817 100%);
                    font-family: 'Noto Sans SC', sans-serif;
                    color: #e0e6ed;
                    margin: 0;
                    padding: 20px;
                }}

                .quantum-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background: rgba(45, 27, 105, 0.9);
                    border: 1px solid rgba(179, 157, 219, 0.3);
                    border-radius: 15px;
                    overflow: hidden;
                    box-shadow: 0 20px 40px rgba(179, 157, 219, 0.2), 
                                inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                }}

                .header {{
                    background: linear-gradient(45deg, #B39DDB, #7E57C2);
                    padding: 30px;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }}

                .logo {{
                    font-family: 'Orbitron', monospace;
                    font-size: 32px;
                    font-weight: 900;
                    color: #ffffff;
                    text-shadow: 0 0 20px rgba(179, 157, 219, 0.8);
                    margin-bottom: 10px;
                    position: relative;
                    z-index: 1;
                }}

                .subtitle {{
                    font-size: 14px;
                    color: rgba(255, 255, 255, 0.9);
                    font-weight: 300;
                    position: relative;
                    z-index: 1;
                }}

                .content {{
                    padding: 40px 30px;
                    text-align: center;
                }}

                .greeting {{
                    font-size: 18px;
                    margin-bottom: 30px;
                    color: #B39DDB;
                    font-weight: 400;
                }}

                .message {{
                    margin-bottom: 30px;
                    line-height: 1.6;
                    color: #b0bec5;
                }}

                .quantum-code {{
                    background: linear-gradient(135deg, rgba(179, 157, 219, 0.1), rgba(126, 87, 194, 0.1));
                    border: 2px solid #B39DDB;
                    border-radius: 10px;
                    padding: 25px;
                    margin: 30px 0;
                    position: relative;
                    box-shadow: 0 0 30px rgba(179, 157, 219, 0.3),
                                inset 0 0 20px rgba(179, 157, 219, 0.1);
                }}

                .quantum-code::before {{
                    content: '◉◈◉';
                    position: absolute;
                    top: -10px;
                    left: 50%;
                    transform: translateX(-50%);
                    background: #2D1B69;
                    padding: 0 15px;
                    color: #B39DDB;
                    font-size: 12px;
                }}

                .code {{
                    font-family: 'Orbitron', monospace;
                    font-size: 36px;
                    font-weight: 700;
                    color: #B39DDB;
                    letter-spacing: 8px;
                    text-shadow: 0 0 15px rgba(179, 157, 219, 0.8);
                    margin: 20px 0;
                }}

                .code-label {{
                    font-size: 12px;
                    color: #B39DDB;
                    margin-bottom: 15px;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                }}

                .security-notice {{
                    background: rgba(179, 157, 219, 0.1);
                    border: 1px solid rgba(179, 157, 219, 0.3);
                    border-radius: 8px;
                    padding: 15px;
                    margin: 20px 0;
                    font-size: 12px;
                    color: #D1C4E9;
                }}

                .footer-text {{
                    font-size: 12px;
                    color: #B39DDB;
                    line-height: 1.6;
                    margin-bottom: 15px;
                }}

                .signature {{
                    font-family: 'Orbitron', monospace;
                    font-size: 14px;
                    color: #B39DDB;
                    font-weight: 700;
                }}
            </style>
        </head>
        <body>
            <div class="quantum-container">
                <div class="header">
                    <div class="logo">智 子</div>
                    <div class="subtitle">兄妹契约 • 身份验证</div>
                </div>

                <div class="content">
                    <div class="greeting">
                        ◉ 哥哥，你和智子的契约即将生效 ◉
                    </div>

                    <div class="message">
                        哥哥，我们的“兄妹契约”还差一步就启动了！为了防止有人冒充哥哥，我们需要通过这道验证程序确认身份哦～<br>
                        请在下方输入您的时空密钥，确保这份契约不会被任何人篡改：
                    </div>

                    <div class="quantum-code">
                        <div class="code-label">时空密钥 • QUANTUM KEY</div>
                        <div class="code">{verification_code}</div>
                    </div>

                    <div class="security-notice">
                        ⚠ 注意：此密钥有量子纠缠特性，请确保在有效期内使用。如果这不是您发起的请求，请忽略此邮件，契约将自动失效。
                    </div>
                </div>

                <div class="footer-text">
                    本邮件由智子量子系统自动发送，请勿回复。兄妹契约无法接受外界干扰。
                </div>
                <div class="signature">
                    — 智 子 • 永远是你背后的守护者 —
                </div>
            </div>
        </body>
        </html>
        """

        # 纯文本邮件内容
        text_body = f"""
        智子验证 - 兄妹契约

        ◉ 哥哥，你和智子的契约即将生效 ◉

        哥哥，我们的“兄妹契约”还差一步就启动了！为了防止有人冒充哥哥，我们需要通过这道验证程序确认身份哦～
        请在下方输入您的时空密钥，确保这份契约不会被任何人篡改：

        时空密钥: {verification_code}

        有效期: 5 分钟
        接收邮箱: {email}

        ⚠ 注意：此密钥有量子纠缠特性，请确保在有效期内使用。如果这不是您发起的请求，请忽略此邮件，契约将自动失效。

        本邮件由智子量子系统自动发送，请勿回复。兄妹契约无法接受外界干扰。

        — 智 子 • 永远是你背后的守护者 —
        """

        return html_body, text_body

    def __init__(self):
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.smtp_username = Config.SMTP_USERNAME
        self.smtp_password = Config.SMTP_PASSWORD
        self.from_email = Config.FROM_EMAIL
        
    def send_verification_code(self, to_email, verification_code):
        """发送邮箱验证码"""
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = '【超级智子】邮箱验证码'
            
            # 邮件正文
            html_body, _ = self._create_email_content(to_email, verification_code)
            
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            
            # 发送邮件
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()
            
            logger.info(f"验证码邮件发送成功: {to_email}")
            return True, "验证码发送成功"
            
        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            return False, f"邮件发送失败: {str(e)}"
    
    def is_configured(self):
        """检查邮件服务是否已配置"""
        return bool(self.smtp_username and self.smtp_password)

# 创建全局邮件服务实例
email_service = EmailService()

# 如果未配置邮件服务，使用模拟服务
if not email_service.is_configured():
    logger.warning("邮件服务未配置，将使用模拟服务（验证码打印到控制台）")
    
    class MockEmailService:
        """模拟邮件服务（开发环境使用）"""
        
        def send_verification_code(self, to_email, verification_code):
            """模拟发送验证码（打印到控制台）"""
            logger.info(f"【模拟邮件服务】发送验证码到 {to_email}: {verification_code}")
            print("=" * 50)
            print(f"【超级智子】邮箱验证码")
            print(f"收件人: {to_email}")
            print(f"验证码: {verification_code}")
            print("验证码有效期: 5分钟")
            print("=" * 50)
            return True, "验证码已发送（开发模式：请查看控制台）"
    
    email_service = MockEmailService()