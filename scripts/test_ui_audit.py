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
driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width': 1920, 'height': 1080, 'deviceScaleFactor': 1, 'mobile': False})

try:
    driver.get('http://localhost:5173')
    time.sleep(2)
    # Click Real Data
    btn = driver.find_element(By.XPATH, "//button[contains(text(), 'REAL DATA') or contains(text(), 'LOAD REAL DATA')]")
    btn.click()
    print("Clicked Real Data")
    time.sleep(3)
    driver.save_screenshot('current_live_app_real_clicked.png')
    print("Saved current_live_app_real_clicked.png")
finally:
    driver.quit()
