"""
Selenium element marker injection feature demonstration test
Demonstrates the element marker injection feature inspired by browser-use for Selenium
"""
import time

import pytest
from dotenv import load_dotenv
from selenium import webdriver

from autowing.selenium import create_fixture


@pytest.fixture(scope="session")
def driver():
    """
    Create and configure Edge WebDriver instance.
    """
    load_dotenv()

    options = webdriver.ChromeOptions()
    options.add_argument('--disable-web-security')
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)

    yield driver
    driver.quit()


@pytest.fixture
def ai(driver):
    """
    ai fixture with element marker injection enabled
    """
    ai_fixture = create_fixture()
    ai_instance = ai_fixture(driver)

    # Enable element marker injection (enabled by default)
    ai_instance.enable_marker_injection(True)

    return ai_instance


def test_selenium_element_marker_demo(ai, driver):
    """
    Demonstrate element marker injection functionality for Selenium
    Demonstrates element marker injection functionality
    """
    # Navigate to test page
    driver.get("https://httpbin.org/forms/post")
    time.sleep(2)  # Wait for page to load

    # View marker injection effect
    print("🔍 Selenium Element Marker Injection Demo")
    print("=" * 50)

    # Perform some operations to trigger marker injection
    ai.ai_query('string[], all input boxes placeholder attributes')

    # Display injected marker information
    context = ai._get_page_context()
    markers = context.get('elementMarkers', {})

    print(f"📊 Number of elements with injected markers: {len(markers)}")
    print("\n🏷️  Marker Details:")
    for marker_id, marker_info in list(markers.items())[:5]:  # Show only first 5
        print(f"  ID: {marker_id}")
        print(f"  Tag: {marker_info.get('tagName')}")
        print(f"  Type: {marker_info.get('type')}")
        print(f"  Placeholder: {marker_info.get('placeholder')}")
        print(f"  Text Content: {marker_info.get('textContent')[:30]}...")
        print("-" * 30)

    # Use AI to perform precise operations
    print("\n🎯 AI Precise Operation Demo:")

    # Traditional fuzzy matching
    print("1. Traditional Method - Fuzzy Matching:")
    try:
        ai.ai_action('Enter "Zhang San" in the name input box')
        print("   ✅ Successfully executed")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

    # Precise matching using markers
    print("2. Marker Method - Precise Matching:")
    try:
        # Here AI will prioritize using marker ID for positioning
        ai.ai_action('Enter "zhangsan@example.com" in the email input box')
        print("   ✅ Successfully executed")
    except Exception as e:
        print(f"   ❌ Failed: {e}")


def test_selenium_marker_performance_comparison(ai, driver):
    """
    Compare performance differences with and without marker injection for Selenium
    Compare performance with and without marker injection
    """
    driver.get("https://httpbin.org/forms/post")
    time.sleep(2)

    # Disable marker injection
    ai.enable_marker_injection(False)

    print("⚡ Selenium Performance Comparison Test")
    print("=" * 50)

    # Test execution time without markers
    start_time = time.time()
    ai.ai_action('Enter "Test User" in the name input box')
    no_marker_time = time.time() - start_time

    # Enable marker injection
    ai.enable_marker_injection(True)

    # Test execution time with markers
    start_time = time.time()
    ai.ai_action('Enter "test@example.com" in the email input box')
    with_marker_time = time.time() - start_time

    print(f"❌ Execution time without marker injection: {no_marker_time:.3f} seconds")
    print(f"✅ Execution time with marker injection: {with_marker_time:.3f} seconds")
    print(f"📈 Performance improvement: {((no_marker_time - with_marker_time) / no_marker_time * 100):.1f}%")


def test_selenium_marker_consistency(ai, driver):
    """
    Test consistency of element marker injection across different page states
    """
    print("🔄 Selenium Marker Consistency Test")
    print("=" * 50)

    # Test multiple pages
    test_urls = [
        "https://httpbin.org/forms/post",
        "https://httpbin.org/html",
        "https://httpbin.org/links/10"
    ]

    for url in test_urls:
        print(f"\nTesting URL: {url}")
        driver.get(url)
        time.sleep(1)

        try:
            context = ai._get_page_context()
            markers = context.get('elementMarkers', {})
            elements = context.get('elements', [])

            print(f"  🏷️  Markers injected: {len(markers)}")
            print(f"  📊 Elements found: {len(elements)}")

            # Verify markers are properly associated with elements
            marker_ids = set(markers.keys())
            element_marker_ids = {elem.get('autowingId') for elem in elements if elem.get('autowingId')}

            if marker_ids and element_marker_ids:
                overlap = marker_ids.intersection(element_marker_ids)
                print(f"  🔗 Marker-element association: {len(overlap)}/{len(marker_ids)} matched")

        except Exception as e:
            print(f"  ❌ Failed: {e}")


if __name__ == '__main__':
    pytest.main(["test_selenium_element_markers.py", "-s", "-v"])
