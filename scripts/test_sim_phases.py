from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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
    # Switch to Real Data
    btn = driver.find_element(By.XPATH, "//button[contains(text(), 'REAL DATA') or contains(text(), 'LOAD REAL DATA')]")
    btn.click()
    time.sleep(2.5)

    # Click simulation
    sim_btn = driver.find_element(By.CLASS_NAME, "demo-sim-btn")
    sim_btn.click()
    print("Clicked Run Counterfactual Simulation")

    time.sleep(0.5)
    driver.save_screenshot("test_phase1.png")
    print("Saved test_phase1.png")

    time.sleep(1.4)
    driver.save_screenshot("test_phase2.png")
    print("Saved test_phase2.png")

    time.sleep(1.4)
    driver.save_screenshot("test_phase3.png")
    print("Saved test_phase3.png")

    time.sleep(4.5)
    driver.save_screenshot("test_post_sim.png")
    print("Saved test_post_sim.png")

finally:
    driver.quit()
