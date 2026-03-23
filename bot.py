import asyncio
import random
import aiohttp
import time
import nest_asyncio
from aiohttp_proxy import ProxyConnector
from playwright.async_api import async_playwright

# تفعيل nest_asyncio للسماح بتشغيل asyncio داخل Colab
nest_asyncio.apply()

# --- الإعدادات ---
TARGET = "https://ouo.io/umzOBoU"
PROXIES_FILE = "proxies.txt"
CONCURRENT_COUNT = 15  # عدد العمليات المتوازية (يمكنك زيادتها حسب قوة النت)

# ----------------- تطوير سحب البروكسيات وفلترتها -----------------
async def fetch_proxies_fast():
    urls = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=1000&country=all&ssl=all&anonymity=all",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=1000&country=all",
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=1000&country=all",
        "https://www.proxy-list.download/api/v1/get?type=https",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"
    ]
    
    unique_proxies = set()
    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url, timeout=10) as resp:
                    text = await resp.text()
                    lines = text.splitlines()
                    for p in lines:
                        if ":" in p:
                            p = p.strip()
                            if "socks4" in url: unique_proxies.add(f"socks4://{p}")
                            elif "socks5" in url: unique_proxies.add(f"socks5://{p}")
                            else: unique_proxies.add(f"http://{p}")
            except:
                continue
    return list(unique_proxies)

async def auto_update_proxies(proxies_list, file_path):
    while True:
        print(f"\n[Auto-Proxy] 🔄 جاري تحديث البروكسيات من {len(proxies_list)} حالياً...", flush=True)
        new_raw_list = await fetch_proxies_fast()
        if new_raw_list:
            proxies_list.clear()
            proxies_list.extend(new_raw_list)
            with open(file_path, "w") as f:
                f.write("\n".join(new_raw_list))
            print(f"[Auto-Proxy] ✅ تم تحديث القائمة إلى {len(proxies_list)} بروكسي!", flush=True)
        await asyncio.sleep(600) # تحديث كل 10 دقائق

# ----------------- وظائف الأتمتة والضغط -----------------
async def block_resources(route):
    if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()

async def attack_cycle(browser, proxy_url, sem):
    async with sem:
        context = None
        try:
            # تهيئة المتصفح مع البروكسي وإعدادات Colab
            context = await browser.new_context(
                proxy={"server": proxy_url},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                ignore_https_errors=True
            )
            page = await context.new_page()
            await page.route("**/*", block_resources)

            print(f"[Bot] 🚀 محاولة دخول: {proxy_url[-20:]}", flush=True)
            # تقليل التايم أوت لضمان عدم تعليق العملية ببروكسي بطيء
            await page.goto(TARGET, timeout=45000, wait_until="domcontentloaded")
            
            for click_num in [1, 2]:
                btn = page.locator("#btn-main")
                await btn.wait_for(state="visible", timeout=10000)
                await asyncio.sleep(1)
                await btn.click(force=True)
                print(f"[Bot] ✅ ضغطة ({click_num}/2) ناجحة", flush=True)
                await asyncio.sleep(2)
                
        except Exception:
            pass # تجاهل أخطاء البروكسيات الميتة
        finally:
            if context:
                await context.close()

async def worker_loop(browser, proxies_list, sem):
    while True:
        if not proxies_list:
            await asyncio.sleep(5)
            continue
        proxy_url = random.choice(proxies_list)
        await attack_cycle(browser, proxy_url, sem)
        await asyncio.sleep(random.uniform(1, 3))

async def main():
    proxies = []
    # تشغيل تحديث البروكسيات في الخلفية
    asyncio.create_task(auto_update_proxies(proxies, PROXIES_FILE))

    # انتظار أول دفعة بروكسيات لتبدأ العمليات
    print("⏳ بانتظار جلب أول قائمة بروكسيات...")
    while not proxies:
        await asyncio.sleep(2)

    print(f"🔥 تم بدء البوت بـ {CONCURRENT_COUNT} عمليات متوازية...")
    
    async with async_playwright() as playwright:
        # إعدادات خاصة بـ Colab لضمان استقرار Chromium
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        
        sem = asyncio.Semaphore(CONCURRENT_COUNT)
        tasks = [asyncio.create_task(worker_loop(browser, proxies, sem)) for _ in range(CONCURRENT_COUNT)]
        
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم.")
