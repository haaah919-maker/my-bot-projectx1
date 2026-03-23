import asyncio
import random
import aiohttp
import os
import nest_asyncio
from playwright.async_api import async_playwright

# تفعيل nest_asyncio للعمل في البيئات السحابية
nest_asyncio.apply()

# --- الإعدادات الذكية ---
TARGET = "https://ouo.io/umzOBoU"
PROXIES_FILE = "proxies.txt"
# تم تقليل العدد لضمان استقرار الرام (2GB كحد أقصى للسبيس)
CONCURRENT_COUNT = 3 
# اسم السبيس للتعريف في التقرير
SPACE_ID = os.getenv('SPACE_ID', 'Space-Default')

# ----------------- جلب البروكسيات -----------------
async def fetch_proxies_fast():
    urls = [
        "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=1000&country=all&ssl=all&anonymity=all",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/shiftytr/proxy-list/master/proxy.txt"
    ]
    
    unique_proxies = set()
    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url, timeout=10) as resp:
                    text = await resp.text()
                    for p in text.splitlines():
                        if ":" in p:
                            unique_proxies.add(f"http://{p.strip()}")
            except:
                continue
    return list(unique_proxies)

async def auto_update_proxies(proxies_list):
    while True:
        print(f"[{SPACE_ID}] 🔄 جاري تحديث قائمة البروكسيات...")
        new_list = await fetch_proxies_fast()
        if new_list:
            proxies_list.clear()
            proxies_list.extend(new_list)
            print(f"[{SPACE_ID}] ✅ تم جلب {len(proxies_list)} بروكسي.")
        await asyncio.sleep(600) # تحديث كل 10 دقائق

# ----------------- فلترة الموارد لتوفير الرام -----------------
async def block_resources(route):
    # منع الصور، الخطوط، التنسيقات، والإعلانات لتقليل استهلاك المعالج والرام
    bad_types = ["image", "media", "font", "stylesheet", "other"]
    bad_urls = ["google-analytics", "doubleclick", "adsbygoogle", "facebook"]
    
    if route.request.resource_type in bad_types or any(x in route.request.url for x in bad_urls):
        await route.abort()
    else:
        await route.continue_()

# ----------------- دورة الضغط -----------------
async def attack_cycle(browser, proxy_url, sem):
    async with sem:
        context = None
        try:
            # إعدادات التخفي وتقليل الموارد
            context = await browser.new_context(
                proxy={"server": proxy_url},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={'width': 800, 'height': 600} # تصغير الشاشة يوفر رام
            )
            page = await context.new_page()
            # تطبيق فلتر الموارد
            await page.route("**/*", block_resources)

            print(f"[{SPACE_ID}] 🚀 دخول عبر: {proxy_url[-15:]}")
            
            # محاولة الدخول مع تايم أوت معقول
            await page.goto(TARGET, timeout=60000, wait_until="domcontentloaded")
            
            # تنفيذ الضغطات (تعديل حسب زر الموقع)
            for click_num in [1, 2]:
                btn = page.locator("#btn-main")
                await btn.wait_for(state="visible", timeout=15000)
                await asyncio.sleep(random.uniform(1, 3)) # محاكاة بشرية
                await btn.click(force=True)
                print(f"[{SPACE_ID}] ✅ ضغطة {click_num} ناجحة.")
                await asyncio.sleep(2)
                
        except Exception as e:
            # أخطاء البروكسي طبيعية، نتجاهلها للاستمرار
            pass 
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
        # استراحة قصيرة بين الدورات لعدم حرق المعالج
        await asyncio.sleep(random.uniform(2, 5))

async def main():
    proxies = []
    asyncio.create_task(auto_update_proxies(proxies))

    while not proxies:
        await asyncio.sleep(2)

    async with async_playwright() as playwright:
        # إعدادات الانطلاق الصامتة والأكثر خفة
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--single-process', # تشغيل كل شيء في عملية واحدة لتوفير الرام
                '--no-zygote'
            ]
        )
        
        sem = asyncio.Semaphore(CONCURRENT_COUNT)
        tasks = [asyncio.create_task(worker_loop(browser, proxies, sem)) for _ in range(CONCURRENT_COUNT)]
        
        print(f"[{SPACE_ID}] 🔥 البوت شغال الآن بـ {CONCURRENT_COUNT} عمال...")
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
