"""一键运行入口"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def run_q1():
    from src.q1_analysis import main as q1_main
    q1_main()


def run_q2():
    from src.q2_classify import main as q2_main
    q2_main()


def run_q3():
    from src.q3_optimizer import main as q3_main
    q3_main()


def run_q4():
    from src.q4_uncertainty import main as q4_main
    q4_main()


def run_all():
    print('=== 问题1 ===')
    run_q1()
    print('\n=== 问题2 ===')
    run_q2()
    print('\n=== 问题3 ===')
    run_q3()
    print('\n=== 问题4 ===')
    run_q4()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python main.py [q1|q2|q3|q4|all]')
    else:
        cmd = sys.argv[1].lower()
        {'q1': run_q1, 'q2': run_q2, 'q3': run_q3, 'q4': run_q4, 'all': run_all}.get(cmd, lambda: print('未知命令'))()
