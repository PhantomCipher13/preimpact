from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(options=options)

try:
    # Inject network request intercept via CDP to fail /api/real with 503
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {'urls': ['*localhost:8000/api/real*', '*127.0.0.1:8000/api/real*']})

    print("Navigating to frontend with /api/real blocked...")
    driver.get('http://localhost:5173')
    
    # Wait for fallback warning or demo badge
    WebDriverWait(driver, 10).until(
        lambda d: d.find_elements(By.CLASS_NAME, 'api-warning') or d.find_elements(By.CLASS_NAME, 'badge-fallback') or d.find_elements(By.CLASS_NAME, 'badge-demo')
    )
    time.sleep(2.0)
    driver.save_screenshot('visual_validation/09_fallback_mode_test.png')
    print("Saved 09_fallback_mode_test.png")

    # Verify no white screen
    body_text = driver.find_element(By.TAG_NAME, 'body').text
    assert 'PREIMPACT' in body_text, "PREIMPACT header missing!"
    assert 'CYCLONE SCENARIO' in body_text, "Cyclone banner missing!"
    print("Graceful fallback test PASSED! Application renders cleanly with honest warning.")

finally:
    driver.quit()
