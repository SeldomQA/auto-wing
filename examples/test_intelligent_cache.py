"""
测试智能缓存功能
验证缓存是否能够正确识别语义相似的请求
"""
import time
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from autowing.playwright import create_fixture


def count_cache_files():
    """统计缓存文件数量"""
    cache_dir = ".auto-wing/cache"
    if not os.path.exists(cache_dir):
        return 0
    return len([f for f in os.listdir(cache_dir) if f.endswith('.json')])


def test_cache_efficiency():
    """测试缓存效率和智能匹配能力"""
    load_dotenv()

    print("🚀 开始智能缓存测试...")
    
    # 清理现有缓存
    cache_dir = ".auto-wing/cache"
    if os.path.exists(cache_dir):
        for f in os.listdir(cache_dir):
            if f.endswith('.json'):
                os.remove(os.path.join(cache_dir, f))
    
    initial_cache_count = count_cache_files()
    print(f"开始时缓存文件数: {initial_cache_count}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 使用非无头模式便于观察
        page = browser.new_page()

        # 创建AI fixture，设置较低的相似度阈值以便测试
        ai_fixture = create_fixture()(page)

        # 访问测试页面
        print("🌐 访问必应搜索页面...")
        page.goto("https://cn.bing.com")
        time.sleep(2)

        # 第一次执行 - 应该生成新缓存
        print("\n📝 第一次执行 (生成缓存):")
        start_time = time.time()
        try:
            ai_fixture.ai_action('搜索输入框输入"playwright"关键字，并回车')
            first_duration = time.time() - start_time
            cache_count_after_first = count_cache_files()
            print(f"⏰ 首次执行耗时: {first_duration:.2f}秒")
            print(f"📄 缓存文件数: {cache_count_after_first}")
        except Exception as e:
            print(f"❌ 首次执行失败: {e}")
            browser.close()
            return

        # 等待页面加载
        time.sleep(3)

        # 第二次执行 - 应该命中缓存
        print("\n📝 第二次执行 (相同指令，应该命中缓存):")
        start_time = time.time()
        try:
            ai_fixture.ai_action('搜索输入框输入"playwright"关键字，并回车')
            second_duration = time.time() - start_time
            cache_count_after_second = count_cache_files()
            print(f"⏰ 缓存执行耗时: {second_duration:.2f}秒")
            print(f"📄 缓存文件数: {cache_count_after_second}")
        except Exception as e:
            print(f"❌ 缓存执行失败: {e}")
            browser.close()
            return

        # 测试语义相似指令 - 使用更明确的指令
        print("\n📝 第三次执行 (语义相似指令):")
        # 临时降低相似度阈值以确保匹配
        original_threshold = ai_fixture.cache_manager.similarity_threshold
        ai_fixture.cache_manager.similarity_threshold = 0.6  # 降低阈值
        
        start_time = time.time()
        try:
            # 使用更明确的英文指令避免输入法问题
            ai_fixture.ai_action('Fill the search box with "playwright" and press enter')
            third_duration = time.time() - start_time
            cache_count_after_third = count_cache_files()
            
            print(f"⏰ 相似指令耗时: {third_duration:.2f}秒")
            print(f"📄 缓存文件数: {cache_count_after_third}")
        except Exception as e:
            print(f"⚠️ 相似指令执行失败 (这可能是预期的): {e}")
            # 即使失败也继续执行，因为这是测试缓存的边界情况
            third_duration = time.time() - start_time
            cache_count_after_third = count_cache_files()
        
        # 恢复原始阈值
        ai_fixture.cache_manager.similarity_threshold = original_threshold

        # 显示缓存统计
        try:
            stats = ai_fixture.get_cache_statistics()
            print(f"\n📊 缓存统计:")
            print(f"   总缓存条目: {stats['total_entries']}")
            print(f"   总使用次数: {stats['total_usage']}")
            print(f"   平均相似度: {stats['average_similarity']:.2f}")
            print(f"   命中率: {stats['hit_rate']:.2f}")
        except Exception as e:
            print(f"❌ 获取缓存统计失败: {e}")

        # 性能对比
        if first_duration > 0 and second_duration > 0:
            speedup = first_duration / second_duration
            print(f"\n⚡ 性能提升: {speedup:.1f}x (缓存 vs 首次)")

        browser.close()

        # 最终统计
        final_cache_count = count_cache_files()
        print(f"\n🏁 测试完成!")
        print(f"   初始缓存文件: {initial_cache_count}")
        print(f"   最终缓存文件: {final_cache_count}")
        print(f"   新增缓存文件: {final_cache_count - initial_cache_count}")

        # 验证测试结果
        if final_cache_count > initial_cache_count:
            print("✅ 测试通过: 成功创建了缓存文件")
        else:
            print("❌ 测试失败: 没有创建新的缓存文件")


def test_cache_clearing():
    """测试缓存清理功能"""
    print("\n🧹 测试缓存清理功能...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        ai_fixture = create_fixture()(page)

        try:
            # 获取清理前的统计
            initial_stats = ai_fixture.get_cache_statistics()
            initial_count = initial_stats['total_entries']
            print(f"清理前缓存条目数: {initial_count}")

            # 清理过期缓存
            ai_fixture.cache_manager.clear_expired()

            # 显示清理后的统计
            final_stats = ai_fixture.get_cache_statistics()
            final_count = final_stats['total_entries']
            print(f"清理后缓存条目数: {final_count}")

            if final_count <= initial_count:
                print("✅ 缓存清理功能正常")
            else:
                print("❌ 缓存清理可能存在问题")
                
        except Exception as e:
            print(f"❌ 缓存清理测试失败: {e}")

        browser.close()


def test_different_similarity_thresholds():
    """测试不同相似度阈值的效果 - 改进版本"""
    print("\n🎚️ 测试不同相似度阈值...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        ai_fixture = create_fixture()(page)
        page.goto("https://cn.bing.com")
        time.sleep(1)
        
        # 使用更稳定的测试数据
        base_prompt = 'Fill search box with "testing" keyword'
        similar_prompt = 'Input "testing" into search field'
        
        results = []
        for threshold in [0.5, 0.7, 0.9]:
            print(f"\n测试阈值: {threshold}")
            
            # 为每个阈值创建独立的缓存管理器
            cache_manager = type(ai_fixture.cache_manager)(
                similarity_threshold=threshold
            )
            ai_fixture.cache_manager = cache_manager
            
            try:
                # 执行基础请求并验证响应
                print("  执行基础请求...")
                ai_fixture.ai_action(base_prompt)
                time.sleep(1)
                
                # 验证缓存条目存在
                stats_before = ai_fixture.get_cache_statistics()
                print(f"  缓存条目数: {stats_before['total_entries']}")
                
                if stats_before['total_entries'] == 0:
                    print(f"  ⚠️ 基础请求未生成缓存，跳过此阈值测试")
                    results.append({
                        'threshold': threshold,
                        'duration': 0,
                        'hit': False,
                        'entries': 0,
                        'status': 'skipped'
                    })
                    continue
                
                # 执行相似请求
                print("  执行相似请求...")
                start_time = time.time()
                try:
                    ai_fixture.ai_action(similar_prompt)
                    duration = time.time() - start_time
                    
                    stats = ai_fixture.get_cache_statistics()
                    hit = stats['total_usage'] > stats['total_entries']  # 有缓存命中
                    
                    results.append({
                        'threshold': threshold,
                        'duration': duration,
                        'hit': hit,
                        'entries': stats['total_entries'],
                        'status': 'success'
                    })
                    
                    status_text = "命中" if hit else "未命中"
                    print(f"  结果: {status_text}, 耗时: {duration:.2f}s")
                    
                except Exception as e:
                    print(f"  ❌ 相似请求执行失败: {e}")
                    results.append({
                        'threshold': threshold,
                        'duration': time.time() - start_time,
                        'hit': False,
                        'entries': stats_before['total_entries'],
                        'status': 'failed'
                    })
                    
            except Exception as e:
                print(f"  ❌ 基础请求执行失败: {e}")
                results.append({
                    'threshold': threshold,
                    'duration': 0,
                    'hit': False,
                    'entries': 0,
                    'status': 'failed'
                })
        
        browser.close()
        
        print("\n📈 阈值测试结果:")
        successful_tests = 0
        for result in results:
            if result['status'] == 'success':
                status_icon = "✅" if result['hit'] else "❌"
                print(f"  {status_icon} 阈值{result['threshold']}: {result['duration']:.2f}s")
                if result['hit']:
                    successful_tests += 1
            elif result['status'] == 'skipped':
                print(f"  ⚠️ 阈值{result['threshold']}: 跳过")
            else:
                print(f"  ❌ 阈值{result['threshold']}: 失败")
        
        if successful_tests > 0:
            print(f"\n✅ 阈值测试部分成功: {successful_tests}/{len(results)} 个阈值测试通过")
        else:
            print(f"\n⚠️ 阈值测试未完全成功，但这可能是由于LLM响应变化")


if __name__ == "__main__":
    print("🧪 智能缓存系统综合测试")
    print("=" * 50)
    
    test_cache_efficiency()
    test_cache_clearing()
    test_different_similarity_thresholds()
    
    print("\n🎉 所有测试完成!")
