import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

os.makedirs("visual_validation", exist_ok=True)

options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
driver = webdriver.Chrome(options=options)

try:
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1920, "height": 1080, "deviceScaleFactor": 1, "mobile": False
    })

    print("--- 1. Testing Fresh Application Load (Expected: Auto REAL OSM) ---")
    driver.get("http://localhost:5173")
    
    # Wait for REAL OSM data badge to appear automatically
    WebDriverWait(driver, 10).until(
        lambda d: "REAL OSM" in d.find_element(By.CLASS_NAME, "data-mode-badge").text
    )
    time.sleep(2.0)

    # State 1: Initial REAL OSM state
    driver.save_screenshot("visual_validation/01_initial_real_osm.png")
    print("Saved 01_initial_real_osm.png")

    # State 2: Bridge B006 selected before simulation
    # Verify B006 details in right panel and open bridge icon
    driver.save_screenshot("visual_validation/02_bridge_b006_before_sim.png")
    print("Saved 02_bridge_b006_before_sim.png")

    # Click RUN COUNTERFACTUAL SIMULATION
    sim_btn = driver.find_element(By.CLASS_NAME, "demo-sim-btn")
    sim_btn.click()
    print("Clicked Run Counterfactual Simulation")

    # State 3: Phase 1 baseline (0.0s - 1.4s)
    time.sleep(0.5)
    driver.save_screenshot("visual_validation/03_phase1_baseline.png")
    print("Saved 03_phase1_baseline.png")

    # State 4: Phase 2 bridge unavailable (1.4s - 2.8s)
    time.sleep(1.4)
    driver.save_screenshot("visual_validation/04_phase2_bridge_unavailable.png")
    print("Saved 04_phase2_bridge_unavailable.png")

    # State 5: Phase 3 reroute (2.8s - 7.0s)
    time.sleep(1.4)
    driver.save_screenshot("visual_validation/05_phase3_reroute.png")
    print("Saved 05_phase3_reroute.png")

    # State 6: Final post-simulation state (> 7.0s)
    time.sleep(4.5)
    driver.save_screenshot("visual_validation/06_final_post_sim.png")
    print("Saved 06_final_post_sim.png")

    # Check console logs
    console_logs = driver.get_log('browser')
    severe_errors = [entry for entry in console_logs if entry['level'] == 'SEVERE']
    print(f"Browser severe errors: {len(severe_errors)}")
    if severe_errors:
        for err in severe_errors:
            print("  SEVERE:", err['message'])

    print("--- 2. Testing 1366x768 Laptop Resolution ---")
    driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1366, "height": 768, "deviceScaleFactor": 1, "mobile": False
    })
    time.sleep(1.0)
    driver.save_screenshot("visual_validation/07_laptop_1366x768_initial.png")
    print("Saved 07_laptop_1366x768_initial.png")

finally:
    driver.quit()

print("All visual validation screenshots completed successfully!")
