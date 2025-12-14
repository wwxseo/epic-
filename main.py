import requests
import os
from datetime import datetime

# 1. 获取 GitHub Secrets
BOT_TOKEN = os.environ.get("TG_BOT_TOKEN")
CHAT_ID = os.environ.get("TG_CHAT_ID")

def get_epic_free_games():
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    try:
        res = requests.get(url).json()
        games = res['data']['Catalog']['searchStore']['elements']
        
        free_games = []
        for game in games:
            # ---------------- 过滤逻辑 ----------------
            # 1. 跳过没有促销信息的
            promotions = game.get('promotions')
            if not promotions:
                continue
            
            # 2. 跳过没有当前优惠的
            if not promotions.get('promotionalOffers'):
                continue
            
            # 3. 【新】只保留游戏本体 (BASE_GAME)，过滤掉 DLC
            # 如果 offerType 为空也保留，防止漏掉某些特殊游戏
            offer_type = game.get('offerType')
            if offer_type and offer_type != 'BASE_GAME':
                continue

            # 4. 检查价格是否为 0
            offers = promotions['promotionalOffers']
            if not offers:
                continue

            is_free = False
            end_date_str = "未知" # 截止时间

            for offer_group in offers:
                for offer in offer_group['promotionalOffers']:
                    if offer['discountSetting']['discountPercentage'] == 0:
                        is_free = True
                        # 提取截止时间
                        raw_date = offer.get('endDate')
                        if raw_date:
                            # 简单格式化时间：2025-12-14T16:00:00.000Z -> 2025-12-14 16:00
                            try:
                                dt = datetime.strptime(raw_date.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                end_date_str = dt.strftime("%Y-%m-%d %H:%M") + " (UTC)"
                            except:
                                end_date_str = raw_date
                        break
            
            # ---------------- 提取信息 ----------------
            if is_free:
                title = game.get('title')
                description = game.get('description', '暂无描述')
                
                # 获取链接 slug
                slug = game.get('productSlug') or game.get('urlSlug')
                link = f"https://store.epicgames.com/p/{slug}" if slug else "https://store.epicgames.com/free-games"
                
                # 【新】获取封面图片 (优先找 Thumbnail，没有就找 Wide)
                image_url = ""
                for img in game.get('keyImages', []):
                    if img.get('type') == 'Thumbnail':
                        image_url = img.get('url')
                        break
                    elif img.get('type') == 'OfferImageWide':
                        image_url = img.get('url')

                free_games.append({
                    "title": title,
                    "description": description,
                    "link": link,
                    "image": image_url,
                    "end_date": end_date_str
                })
                
        return free_games
        
    except Exception as e:
        print(f"获取 Epic 数据出错: {e}")
        return []

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ 错误：未设置 Token 或 Chat ID")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown", 
        "disable_web_page_preview": False # 开启预览以便显示图片
    }
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            print("✅ 消息推送成功")
        else:
            print(f"❌ 推送失败: {res.text}")
    except Exception as e:
        print(f"❌ 请求错误: {e}")

if __name__ == "__main__":
    print("⏳ 开始检查 Epic 免费游戏...")
    games = get_epic_free_games()
    
    if games:
        print(f"🎉 发现 {len(games)} 个免费游戏")
        
        # 遍历每个游戏发送一条单独的消息（体验更好，图片显示更准）
        for g in games:
            # 使用零宽字符 [\u200b] 让 Telegram 抓取图片作为预览，但不显示 URL 文本
            msg = (
                f"[\u200b]({g['image']})\n"
                f"🔥 **Epic 喜加一提醒** 🔥\n\n"
                f"🎮 **{g['title']}**\n"
                f"⏰ 截止: {g['end_date']}\n\n"
                f"📝 {g['description']}\n\n"
                f"🔗 [点击领取游戏]({g['link']})"
            )
            send_telegram_message(msg)
            
    else:
        print("🤷‍♂️ 当前没有检测到免费游戏 (或接口变动)")
