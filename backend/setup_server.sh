#!/bin/bash
# SugarClaw 服务器一键配置脚本

# 1. 配置 nginx
cat > /etc/nginx/sites-available/sugarclaw << 'NGINX'
server {
    listen 80;
    server_name sugarclaw.top;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_read_timeout 120s;
        chunked_transfer_encoding on;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/sugarclaw /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
echo "✓ nginx 配置完成"

# 2. 开放 80/443 端口
ufw allow 80/tcp
ufw allow 443/tcp
ufw reload
echo "✓ 防火墙端口已开放"

# 3. 配置开机自启
cat > /etc/systemd/system/sugarclaw.service << 'SERVICE'
[Unit]
Description=SugarClaw Backend
After=network.target

[Service]
WorkingDirectory=/root/SugarClaw/backend
Environment="DEEPSEEK_API_KEY=sk-db4877264bb649ae8e48ab445ab30b57"
ExecStart=/root/SugarClaw/backend/.venv/bin/uvicorn api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable sugarclaw
systemctl restart sugarclaw
echo "✓ 开机自启配置完成"

echo ""
echo "=== 全部完成 ==="
echo "等域名实名认证通过后运行："
echo "certbot --nginx -d sugarclaw.top --non-interactive --agree-tos -m your@email.com"
