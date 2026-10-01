import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

os.makedirs("demo_frames/scroll", exist_ok=True)

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
driver = webdriver.Chrome(options=options)

try:
    driver.get("http://localhost:5173")
    time.sleep(2)
    driver.find_element(By.XPATH, "//button[contains(., 'REAL DATA') or contains(., 'LOAD REAL DATA')]").click()
    WebDriverWait(driver, 15).until(lambda d: "REAL OSM" in d.find_element(By.CLASS_NAME, "data-mode-badge").text or "PARTIAL" in d.find_element(By.CLASS_NAME, "data-mode-badge").text)
    time.sleep(2)

    # Trigger simulation so phase 3 is active
    driver.find_element(By.CLASS_NAME, "demo-sim-btn").click()
    time.sleep(3.6) # Wait for phase 3 to complete

    right_panel = driver.find_element(By.CLASS_NAME, "right-panel")
    # capture 10 scroll steps
    for s in range(0, 451, 45):
        driver.execute_script(f"arguments[0].scrollTop = {s};", right_panel)
        time.sleep(0.1)
        driver.save_screenshot(f"demo_frames/scroll/scroll_{s:03d}.png")
        print(f"Captured scroll_{s:03d}.png")
finally:
    driver.quit()
