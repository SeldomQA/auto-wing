"""
Element marker injection feature demonstration test
Demonstrates the element marker injection feature inspired by browser-use
"""
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page

from autowing.playwright import create_fixture


@pytest.fixture
def ai(page):
    """
    AI fixture with element marker injection enabled
    """
    load_dotenv()
    ai_fixture = create_fixture()
    ai_instance = ai_fixture(page)

    # Enable element marker injection (enabled by default)
    ai_instance.enable_marker_injection(True)

    return ai_instance


def test_element_marker_demo(page: Page, ai):
    """
    Demonstrate element marker injection functionality
    Demonstrates element marker injection functionality
    """
    # Navigate to test page
    page.goto("https://httpbin.org/forms/post")

    # View marker injection effect
    print("🔍 Element Marker Injection Demo")
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


def test_marker_performance_comparison(page: Page, ai):
    """
    Compare performance differences with and without marker injection
    Compare performance with and without marker injection
    """
    import time

    page.goto("https://httpbin.org/forms/post")

    # Disable marker injection
    ai.enable_marker_injection(False)

    print("⚡ Performance Comparison Test")
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


if __name__ == '__main__':
    pytest.main(["test_element_markers.py", "-s", "-v"])
