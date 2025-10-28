import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.circuit import Parameter
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Pauli, Statevector, Operator
from qiskit.circuit.controlflow import IfElseOp
from qiskit_ibm_runtime.fake_provider import FakeVigoV2
from qiskit_ibm_runtime import Sampler, RuntimeJobV2

import requests
import json

submission_status = {
    "name": None,
    1: False,
    2: False,
    3: False,
    4: False,
    5: False,
    6: False,
    7: False,
    8: False,
    9: False,
    12: False,
    13: False,
    15: False,
    16: False,
}


def initialize_grader(participant_name: str):
    global submission_status
    submission_status["name"] = participant_name
    problem_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 15, 16]
    for num in problem_numbers:
        submission_status[num] = True

    print("=" * 80)
    print(
        f"    QISKIT FALL FEST @ YONSEI 2025 Beginner Hackathon에 오신것을 환영합니다!"
    )
    print(f"    지금부터 {submission_status['name']}님의 채점 현황이 기록됩니다.")
    print("=" * 80)


def correct():
    print("🎉축하합니다! 정답입니다! 다음 문제로 넘어가세요")


def wrong():
    print("❌ 오답입니다. 코드를 다시한번 확인해보세요.")


def error():
    print("‼️ 오류가 발생했습니다. 코드를 다시 한번 확인하고 문제의 지시를 따라주세요.")
    print("또한 Grader Cell은 수정하지 마세요.")


def grade_p1(user_pauli: Pauli):
    solution_pauli = Pauli("ZYI")

    if not isinstance(user_pauli, Pauli):
        error()
        print(
            f"제출된 객체가 Pauli 클래스가 아닙니다. (제출된 타입: {type(user_pauli)})"
        )
        return

    if user_pauli == solution_pauli:
        correct()
        print("정확한 'ZYI' Pauli 연산자를 생성했습니다.")
        submission_status[1] = True
    else:
        wrong()
        print(f"생성된 연산자가 'ZYI'가 아닙니다. (제출된 값: {user_pauli})")
        submission_status[1] = False


def grade_p2(user_circuit: QuantumCircuit):
    solution_qc = QuantumCircuit(1)
    solution_qc.x(0)
    solution_qc.t(0)
    solution_sv = Statevector(solution_qc)

    if not isinstance(user_circuit, QuantumCircuit):
        error()
        print(
            f"제출된 객체는 QuantumCircuit 클래스가 아닙니다. (제출된 타입: {type(user_circuit)})"
        )
        return

    try:
        user_sv = Statevector(user_circuit)
    except:
        error()
        return

    if user_sv.equiv(solution_sv):
        correct()
        submission_status[2] = True
    else:
        wrong()
        submission_status[3] = False


def grade_p3(user_circuit: QuantumCircuit):
    sv = Statevector(user_circuit)
    probs = sv.probabilities_dict()

    prob0 = probs.get("0", 0)
    prob1 = probs.get("1", 0)

    if np.isclose(prob0, 0.25, atol=0.01) and np.isclose(prob1, 0.75, atol=0.01):
        correct()
        print("올바른 확률 분포를 만들었습니다.")
        submission_status[3] = True
    else:
        wrong()
        print(f"확률 분포가 다릅니다. (결과: P(0)={prob0:.3f}, P(1)={prob1:.3f})")
        submission_status[3] = False


def grade_p4(user_circuit: QuantumCircuit):
    solution_qc = QuantumCircuit(2)
    solution_qc.h(0)
    solution_qc.cx(0, 1)
    solution_sv = Statevector(solution_qc)

    try:
        user_sv = Statevector(user_circuit)
    except:
        error()
        return

    if user_sv.equiv(solution_sv):
        correct()
        print("정확한 벨 상태를 만들었습니다.")
        submission_status[4] = True
    else:
        wrong()
        print("생성된 상태가 올바른 벨 상태가 아닙니다.")
        submission_status[4] = False


def grade_p5(user_circuit: QuantumCircuit):
    # Only check if the participant created the GHZ State correctly
    solution_qc = QuantumCircuit(3)
    solution_qc.h(0)
    solution_qc.cx(0, 1)
    solution_qc.cx(0, 2)
    solution_sv = Statevector(solution_qc)

    if not isinstance(user_circuit, QuantumCircuit) or user_circuit.num_qubits != 3:
        error(0)
        return

    try:
        user_sv = Statevector(user_circuit)
    except:
        error()
        return

    if user_sv.equiv(solution_sv):
        correct()
        print("정확한 GHZ 상태를 생성했습니다.")
        submission_status[5] = True
    else:
        wrong()
        print("생성된 상태가 올바른 GHZ 상태가 아닙니다.")
        submission_status[5] = False


def grade_p6(user_circuit: QuantumCircuit):
    if user_circuit.num_qubits != 2 or user_circuit.num_clbits != 1:
        wrong()
        print("회로는 2개의 큐비트와 1개의 클래시컬 비트를 가져야 합니다.")
        submission_status[6] = False
        return

    if_op_found = None
    if_instr_found = None
    for instr in user_circuit.data:
        if isinstance(instr.operation, IfElseOp):
            if_op_found = instr.operation
            if_instr_found = instr
            break

    if if_op_found is None:
        wrong()
        submission_status[6] = False
        return

    if not if_op_found.blocks or len(if_op_found.blocks) < 1:
        wrong()
        submission_status[6] = False
        return

    true_body_circuit = if_op_found.blocks[0]
    body_ops = [instr.operation.name for instr in true_body_circuit.data]
    if "x" not in body_ops:
        wrong()
        submission_status[6] = False
        return

    x_gate_applied_correctly = False
    for inner_instr in true_body_circuit.data:
        if inner_instr.operation.name == "x":
            qubit_index = user_circuit.qubits.index(inner_instr.qubits[0])
            if qubit_index == 1:
                x_gate_applied_correctly = True
                break

    if not x_gate_applied_correctly:
        wrong()
        submission_status[6] = False
        return

    correct()
    print("모든 요구사항을 완벽하게 만족하는 동적 회로입니다.")
    submission_status[6] = True


def grade_p7(user_counts: dict):
    # Can't check the histogram. So just check if the result dict only has "00" or "11"
    if not isinstance(user_counts, dict):
        error()
        return

    allowed_keys = {"00", "11"}
    actual_keys = set(user_counts.keys())

    if actual_keys == allowed_keys:
        correct()
        print("벨 상태의 올바른 측정 결과 히스토그램입니다.")
        submission_status[7] = True
    else:
        wrong()
        submission_status[7] = False


def grade_p8(parameterized_circuit: QuantumCircuit, bound_circuit: QuantumCircuit):
    # Check the parameterized circuit
    param_check = False
    if (
        parameterized_circuit.num_qubits == 1
        and len(parameterized_circuit.parameters) == 1
        and len(parameterized_circuit.data) == 1
        and parameterized_circuit.data[0].operation.name == "rx"
    ):
        param_check = True

    if not param_check:
        wrong()
        submission_status[8] = False
        return

    # Check bounded qc
    if len(bound_circuit.parameters) > 0:
        wrong()
        print("bound_qc가 잘못됐습니다.")
        submission_status[8] = False
        return

    solution_qc = QuantumCircuit(1)
    solution_qc.rx(np.pi / 2, 0)
    solution_sv = Statevector(solution_qc)

    try:
        user_sv = Statevector(bound_circuit)
        if user_sv.equiv(solution_sv):
            correct()
            submission_status[8] = True
        else:
            wrong()
            submission_status[8] = False
    except:
        error()


def grade_p9(user_transpiled_circuit: QuantumCircuit):
    solution_ghz = QuantumCircuit(3)
    solution_ghz.h(0)
    solution_ghz.cx(0, 1)
    solution_ghz.cx(0, 2)

    backend = FakeVigoV2()
    try:
        pass_manager = generate_preset_pass_manager(
            optimization_level=3, backend=backend
        )
        solution_transpiled = pass_manager.run(solution_ghz)
    except:
        print("🚨 채점기 내부 오류")
        return

    try:
        op_user = Operator(user_transpiled_circuit)
        op_solution = Operator(solution_transpiled)

        if op_user.equiv(op_solution):
            correct()
            print("GHZ 회로를 만들고 성공적으로 트랜스파일링했습니다.")
            print(
                "Transpile된 회로의 깊이가 원본 회로보다 더 깊은 것을 확인할 수 있습니다."
            )
            submission_status[9] = True
        else:
            wrong()
            submission_status[9] = False
    except:
        error()


def grade_p12(user_counts: dict):
    if not isinstance(user_counts, dict):
        error()
        return

    allowed_keys = {"00", "11"}
    actual_keys = set(user_counts.keys())

    if actual_keys == allowed_keys:
        correct()
        submission_status[12] = True
    else:
        invalid_keys = actual_keys - allowed_keys
        if invalid_keys:
            wrong()
            submission_status[12] = False
        else:
            wrong()
            submission_status[12] = False


def grade_p13(user_expectation_value: float):
    if (
        not isinstance(user_expectation_value, np.ndarray)
        and user_expectation_value.size == 1
    ):
        error()
        return

    solution_value = 1.0

    if np.isclose(user_expectation_value, solution_value):
        correct()
        print("정확한 기대값을 계산했습니다.")
        submission_status[13] = True
    else:
        wrong()
        submission_status[13] = False


def grade_p15(user_job):
    if not isinstance(user_job, RuntimeJobV2):
        error()
        print(
            "제출된 객체는 RuntimeJobV2가 아닙니다. Sampler.run()의 결과물을 전달해주세요."
        )
        return

    try:
        job_status = user_job.status()

        print(f"Job ID: {user_job.job_id()}")
        print(f"Job Status: {job_status}")

        if job_status not in ["DONE", "ERROR", "CANCELLED"]:
            print(
                "⏳ 작업이 아직 완료되지 않았습니다. 잠시 후 다시 이 셀을 실행하여 상태를 확인하세요."
            )
        elif job_status == "DONE":
            correct()
            submission_status[15] = True
        else:
            wrong()
            print("작업에 문제가 발생했습니다. 다시 시도해주세요")
            submission_status[15] = False

    except Exception as e:
        error()


class grade_p16:
    def __init__(self):
        self.bases = ["Z", "X"]

    def encode_qubit(self, bit, basis):
        qc = QuantumCircuit(1)
        if bit == 1:
            qc.x(0)
        if basis == "X":
            qc.h(0)
        return qc

    def bb84_test(self, alice, bob, eve, compare_bases, check_eve):
        print("=" * 40)
        print("      BB84 프로토콜 구현 채점을 시작합니다.")
        print("=" * 40)

        try:
            KEY_LENGTH = 200
            EVE_IS_PRESENT = False
            EVE_SUCCESS = False
            NO_EVE_SUCCESS = False

            alice_bits, alice_bases, encoded_qubits = alice(KEY_LENGTH)

            backend = AerSimulator()
            pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
            sampler = Sampler(mode=backend)

            for _ in range(2):
                if EVE_IS_PRESENT:
                    print("=" * 40)
                    print("\n")
                    print("=" * 40)
                    print("2. 🕵️‍♀️ Eve가 도청하는 키분배 테스트입니다...")
                    qubits_for_bob = eve(encoded_qubits, pm, sampler)
                else:
                    print("1. 🕊️ Eve가 없는 키분배 테스트입니다...")
                    qubits_for_bob = encoded_qubits

                bob_bases, bob_results = bob(qubits_for_bob, pm, sampler)

                same_bases_index = compare_bases(alice_bases, bob_bases)

                print(
                    f"기저 비교 결과: 총 {KEY_LENGTH}개 중 {len(same_bases_index)}개의 기저가 일치했습니다."
                )

                final_key, eve_detected = check_eve(
                    alice_bits, bob_results, same_bases_index
                )

                print("-" * 40)
                if not EVE_IS_PRESENT:
                    if not eve_detected and final_key is not None:
                        NO_EVE_SUCCESS = True
                        print(f"✅ 최종 비밀 키가 성공적으로 공유되었습니다!")
                        print(f"   - 최종 키 길이: {len(final_key)}")
                        print(f"   - 최종 비밀키: {np.array(final_key)}")
                    else:
                        print("❌ 키 공유에 실패했습니다.")
                else:
                    EVE_SUCCESS = True
                    print("🎉 Eve를 성공적으로 탐지했습니다!")

                EVE_IS_PRESENT = True

            print("=" * 40)
            print("           테스트 최종 결과")
            print("=" * 40)
            if EVE_SUCCESS and NO_EVE_SUCCESS:
                print("🎉축하합니다! 정답입니다! 다음 셀에서 최종 제출을 해주세요")
                submission_status[16] = True
                return
            else:
                wrong()
                submission_status[16] = False
                return

        except:
            print("\n" + "=" * 40)
            error()
            print("=" * 40)
            return


def check_submission_status():
    participant_name = submission_status.get("name")
    if participant_name is None:
        print("⚠️ 채점기가 아직 초기화되지 않았습니다.")
        return

    print("=" * 40)
    print(f"        '{participant_name}'님의 현재 제출 현황")
    print("=" * 40)

    all_passed = True
    for problem_num, status in submission_status.items():
        if problem_num == "name":
            continue
        print(f"  문제 {problem_num:<2}: {'✅ 통과' if status else '❌ 미완료'}")
        if not status:
            all_passed = False

    return all_passed


submitted = False


def final_submission():
    passed = check_submission_status()
    global submitted

    if not passed:
        print("통과하지 못한 문제가 있습니다. 다시 한번 확인해주세요.")
    else:
        if not submitted:
            try:
                WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwOxgaLv5eKUqSIkaGSH0JIMywZbL8mtc2Z4VZ6CoTD0TmrH_D-PDcPdokdTQu2cyaf/exec"

                payload = {
                    "participant_id": submission_status["name"],
                    "completion_code": "Beginner_Completed",
                }

                response = requests.post(
                    WEB_APP_URL,
                    data=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                    timeout=20,
                )

                if response.status_code == 200:
                    print("완료 기록이 성공적으로 제출되었습니다.")
                    submitted = True
                else:
                    print("완료 기록 제출에 실패했습니다. (서버 응답 없음)")

            except requests.exceptions.RequestException as e:
                print("완료 기록 제출에 실패했습니다. (네트워크 오류)")
        else:
            print("이미 제출되었습니다!")
