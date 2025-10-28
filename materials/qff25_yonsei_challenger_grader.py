import matplotlib.pyplot as plt
import numpy as np

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.quantum_info import SparsePauliOp, Operator
from qiskit.transpiler import CouplingMap
from qiskit.synthesis import LieTrotter
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp, Statevector

from qiskit_addon_obp import backpropagate
from qiskit_addon_obp.utils.simplify import OperatorBudget
from qiskit_addon_obp.utils.truncating import setup_budget

from qiskit_addon_utils.problem_generators import (
    generate_xyz_hamiltonian,
    generate_time_evolution_circuit,
)
from qiskit_addon_utils.slicing import slice_by_gate_types, combine_slices


from qiskit_ibm_runtime import SamplerV2 as Sampler
from qiskit_aer import AerSimulator
import requests
import json

submission_status = {
    "name": None,
    "1_1": False,
    "1_2": False,
    "1_3": False,
    "1_4": False,
    "2_1": False,
    "2_2": False,
    "2_3": False,
    "2_4": False,
    "Challenge": False,
    "Challenge Score": None,
}


def initialize_grader(participant_name: str):
    global submission_status
    submission_status["name"] = participant_name
    problem_numbers = [
        "1_1",
        "1_2",
        "1_3",
        "1_4",
        "1_5",
        "2_1",
        "2_2",
        "2_3",
        "2_4",
        "Challenge",
    ]
    for num in problem_numbers:
        submission_status[num] = False

    submission_status["Challenge Score"] = None

    print("=" * 80)
    print(
        f"    QISKIT FALL FEST @ YONSEI 2025 Challenger Hackathon에 오신것을 환영합니다!"
    )
    print(f"    지금부터 {submission_status['name']}님의 채점 현황이 기록됩니다.")
    print("=" * 80)


def correct():
    print("🎉축하합니다! 정답입니다! 다음 문제로 넘어가세요")


def wrong():
    print("❌ 오답입니다. 코드를 다시한번 확인해보세요.")


def error():
    print("‼️ 오류가 발생했습니다. 코드를 다시 한번 확인하고 문제의 지시를 따라주세요.")
    print("‼️ 또한 Grader Cell은 수정하지 마세요.")


sol_coupling_map = CouplingMap(
    [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9)]
)


def grade_1_1(coupling_map):
    if coupling_map == sol_coupling_map:
        correct()
        submission_status["1_1"] = True
    else:
        wrong()


def grade_1_2(user_hamiltonian: SparsePauliOp, user_circuit: QuantumCircuit):
    sol_hamiltonian = generate_xyz_hamiltonian(
        sol_coupling_map,
        coupling_constants=(np.pi / 8, np.pi / 4, np.pi / 2),
        ext_magnetic_field=(np.pi / 3, np.pi / 6, np.pi / 9),
    )
    sol_circuit = generate_time_evolution_circuit(
        sol_hamiltonian,
        time=0.2,
        synthesis=LieTrotter(reps=2),
    )

    ham_correct = False
    if sol_hamiltonian.equiv(user_hamiltonian):
        ham_correct = True
    else:
        wrong()
        return

    if Statevector(sol_circuit).equiv(Statevector(user_circuit)):
        if ham_correct:
            correct()
            submission_status["1_2"] = True
            return

    else:
        wrong()
        return


def grade_1_3(user_observable: SparsePauliOp):
    num_qubits = 10
    if not isinstance(user_observable, SparsePauliOp):
        error()
        print(f"‼️ 오류: 제출된 객체는 SparsePauliOp이 아닙니다.")
        return
    if user_observable.num_qubits != num_qubits:
        wrong()
        print(f"‼️ 큐비트 수가 올바르지 않습니다.")
        return
    if len(user_observable) != num_qubits:
        print(f"‼️ Observable의 항의 개수가 올바르지 않습니다.")
        return

    expected_coeff = 1 / num_qubits
    found_indices = set()

    try:
        for pauli_str, coeff in user_observable.to_list():
            if not np.isclose(coeff.real, expected_coeff) or coeff.imag != 0:
                wrong()
                return

            x_count = pauli_str.count("X")
            i_count = pauli_str.count("I")
            x_index = -1
            if x_count != 1 or (x_count + i_count) != num_qubits:
                wrong()
                return
            x_index = pauli_str[::-1].find("X")
            if x_index == -1:  # 혹시 모를 에러 방지
                error()
            if x_index in found_indices:
                wrong()
                return
            found_indices.add(x_index)

        if len(found_indices) != num_qubits or found_indices != set(range(num_qubits)):
            wrong()
            return

        correct()
        submission_status["1_3"] = True
        return

    except:
        error()
        return


def grade_1_4(
    user_bp_observable: SparsePauliOp,
    user_bp_circuit: QuantumCircuit,
    original_observable: SparsePauliOp,
    original_circuit: QuantumCircuit,
):

    if not isinstance(user_bp_observable, SparsePauliOp):
        error()
        print("‼️ bp_observable이 SparsePauliOp이 아닙니다.")
        return False
    if not isinstance(user_bp_circuit, QuantumCircuit):
        print("‼️ bp_circuit이 QuantumCircuit이 아닙니다.")
        return False

    try:
        solution_slices = slice_by_gate_types(original_circuit)

        solution_op_budget = OperatorBudget(max_qwc_groups=10)
        solution_trunc_budget = setup_budget(max_error_per_slice=0.005)

        solution_bp_observable, solution_remaining_slices, _ = backpropagate(
            original_observable,
            solution_slices,
            operator_budget=solution_op_budget,
            truncation_error_budget=solution_trunc_budget,
        )
        solution_bp_circuit = combine_slices(
            solution_remaining_slices, include_barriers=False
        )
    except:
        error()
        return

    try:
        observable_match = user_bp_observable.equiv(solution_bp_observable)
        circuit_match = Operator(user_bp_circuit).equiv(Operator(solution_bp_circuit))

        if observable_match and circuit_match:
            correct()
            submission_status["1_4"] = True
            return
        else:
            wrong()
            return

    except Exception as e:
        wrong()
        return


def grade_1_5(qwc_list):
    anwser = [2, 3, 4, 6, 12, 24, 48]
    if qwc_list == anwser:
        correct()
        submission_status["1_5"] = True
    else:
        wrong()
        return


def grade_2_1(user_circuit: QuantumCircuit):
    if not isinstance(user_circuit, QuantumCircuit):
        error()
        print(f"❌ 오류: 제출된 객체는 QuantumCircuit이 아닙니다.")
        return
    if user_circuit.num_qubits != 2 or user_circuit.num_clbits != 1:
        error()
        print(f"‼️ 회로는 2개의 큐비트와 1개의 클래시컬 비트를 가져야 합니다.")
        return

    sol_qc = QuantumCircuit(2, 1)
    sol_qc.h(0)
    sol_qc.cx(0, 1)

    sol_qc.cx(0, 1)
    sol_qc.h(0)

    try:
        user_circuit_copy = user_circuit.copy()
        op_user = Operator(user_circuit_copy.remove_final_measurements(inplace=False))

        if not Operator(sol_qc).equiv(op_user):
            wrong()
            print("HEE")
            return

    except:
        error()
        return

    try:
        user_instructions = user_circuit.data

        if not user_instructions or user_instructions[-1].operation.name != "measure":
            wrong()
            return

        last_instruction = user_instructions[-1]

        measured_qubit = last_instruction.qubits[0]
        target_clbit = last_instruction.clbits[0]

        if (
            measured_qubit != user_circuit.qubits[0]
            or target_clbit != user_circuit.clbits[0]
        ):
            wrong()
            return

    except:
        error()
        return

    correct()
    submission_status["2_1"] = True
    return


def grade_2_2(user_counts: dict):
    incorrect_outcomes = [key for key in user_counts.keys() if key != "0"]
    if not incorrect_outcomes and "0" in user_counts:
        correct()
        submission_status["2_2"] = True
        return
    elif incorrect_outcomes:
        wrong()
        return
    else:
        wrong()
        return


def grade_2_3(user_circuit: QuantumCircuit):
    if not isinstance(user_circuit, QuantumCircuit):
        error()
        print(f"‼️ 오류: 제출된 객체는 QuantumCircuit이 아닙니다.")
        return
    if user_circuit.num_qubits != 2 or user_circuit.num_clbits != 2:
        error()
        print(f"‼️ 회로는 2개의 큐비트와 2개의 클래시컬 비트를 가져야 합니다.")
        return

    sol_qc = QuantumCircuit(2, 2)
    sol_qc.h(0)
    sol_qc.cx(0, 1)
    sol_qc.cx(0, 1)
    sol_qc.h(0)

    user_circuit_copy = user_circuit.copy()

    try:
        user_uni = QuantumCircuit(2, 2)
        for instruction in user_circuit_copy.data:
            if instruction.operation.name not in ["measure", "barrier"]:
                user_uni.append(instruction)
        if not Operator(sol_qc).equiv(Operator(user_uni)):
            wrong()
            return
    except:
        error()
        return

    # Lsst measurement
    try:
        user_instructions = user_circuit.data

        if not user_instructions or user_instructions[-1].operation.name != "measure":
            wrong()
            return

        last_instruction = user_instructions[-1]
        measured_qubit = last_instruction.qubits[0]
        target_clbit = last_instruction.clbits[0]

        if (
            measured_qubit != user_circuit.qubits[0]
            or target_clbit != user_circuit.clbits[0]
        ):
            wrong()
            return
    except:
        error()
        return

    # Bomb measurement
    try:
        for index, instruction in enumerate(user_circuit.data):
            if (
                instruction.operation.name == "barrier"
                and instruction.operation.label == "BOMB"
            ):
                next_instruction = user_circuit.data[index + 1]
                if next_instruction.operation.name == "measure":
                    try:
                        measured_qubit = next_instruction.qubits[0]
                        target_clbit = next_instruction.clbits[0]
                        if (
                            measured_qubit != user_circuit.qubits[1]
                            or target_clbit != user_circuit.clbits[1]
                        ):
                            wrong()
                            return
                    except:
                        error()
                        return
                else:
                    wrong()
                    print('폭탄 앞에 barrier의 label을 "BOMB"으로 했는지 확인해주세요.')
                    return
    except:
        error()
        return

    correct()
    submission_status["2_3"] = True
    return


def grade_2_4(user_counts: dict):
    total_shots = sum(user_counts.values())
    if total_shots != 1024:
        error()
        print("‼️ Sampler의 shot 수를 1024개로 하세요")
        return

    prob_exploded = user_counts["exploded"] / 1024
    prob_detected = user_counts["detected w/o exploding"] / 1024
    prob_dunno = user_counts["NA"] / 1024

    expected_exploded = 0.50
    expected_detected = 0.25
    expected_dunno = 0.25
    tolerance = 0.05

    exploded_ok = np.isclose(prob_exploded, expected_exploded, atol=tolerance)
    detected_ok = np.isclose(prob_detected, expected_detected, atol=tolerance)
    dunno_ok = np.isclose(prob_dunno, expected_dunno, atol=tolerance)

    if exploded_ok and detected_ok and dunno_ok:
        correct()
        submission_status["2_4"] = True
        return
    else:
        wrong()
        return


def get_score(interpreted_counts: dict) -> float:
    total_shots = sum(interpreted_counts.values())
    p_found = interpreted_counts["detected w/o exploding"] / total_shots
    p_exploded = interpreted_counts["exploded"] / total_shots

    score = (2 * p_found - p_exploded + 0.5) * 150

    return score


def ev_score_cal(counts: dict):
    interpreted_counts = {
        "exploded": 0,
        "dunno": 0,
        "detected w/o exploding": 0,
    }
    for outcome, count in counts.items():
        c1 = int(outcome[0])  # BOMB
        c0 = int(outcome[1])  # DETECTOR

        if c1 == 1:  # c1이 1이면 폭탄 터진거임
            interpreted_counts["exploded"] += count
        elif (
            c0 == 0
        ):  # c1c0가 00 이면 detector 2에서 검출된거임. 그냥 뭐 아무일 안일어난거. (폭탄이 있을수도 없을수도)
            interpreted_counts["dunno"] += count
        else:  # c1c0가 01인거니깐 Detector 1에서 광자가 검출된거니깐 폭탄이 있다는 뜻. (폭탄 안터트리고 감지함)
            interpreted_counts["detected w/o exploding"] += count

    score = get_score(interpreted_counts)

    return score


backend = AerSimulator()
pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
sampler = Sampler(mode=backend)


def grade_challenge(user_circuit: QuantumCircuit):
    if not isinstance(user_circuit, QuantumCircuit):
        error()
        print(f"‼️ 오류: 제출된 객체는 QuantumCircuit이 아닙니다.")
        return
    if user_circuit.num_qubits != 2 or user_circuit.num_clbits != 2:
        error()
        print(f"‼️ 오답: 회로는 2개의 큐비트와 2개의 클래시컬 비트를 가져야 합니다.")
        return

    counts = {}
    try:
        isa_user_circuit = pm.run(user_circuit)
        job = sampler.run([user_circuit], shots=2048)
        counts = job.result()[0].data.c.get_counts()

    except:
        error()
        return

    challenge_score = ev_score_cal(counts)
    if challenge_score is not None:
        submission_status["Challenge Score"] = challenge_score
        submission_status["Challenge"] = True
        print(f"Challenge Score: {challenge_score}")
    return


def check_submission_status(participant_name):
    print("=" * 40)
    print(f"        '{participant_name}'님의 현재 제출 현황")
    print("=" * 40)

    all_passed = True
    for key, status in submission_status.items():
        if key == "name" or key == "Challenge Score":
            continue

        print(f"  문제 {key:<2}: {'✅ 통과' if status else '❌ 미완료'}")
        if isinstance(status, bool) and not status:
            all_passed = False
            break

    if all_passed:
        print(f"\n🏆 Challenge Score: {submission_status['Challenge Score']}")

    return all_passed


submitted = False


def final_submission():
    participant_name = submission_status.get("name")
    if participant_name is None:
        print("⚠️ 채점기가 아직 초기화되지 않았습니다.")
        return

    passed = check_submission_status(participant_name)
    if passed:
        final_score = submission_status["Challenge Score"]

    global submitted

    participant_name = submission_status.get("name", "Unknown Participant")

    if not passed:
        print("통과하지 못한 문제가 있습니다. 다시 한번 확인해주세요.")
    else:
        print(
            f"\n🚀 {participant_name}님의 최종 점수 ({final_score:.2f})를 제출합니다..."
        )
        try:
            WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxGwE9x8Z2VQj1iZHUvAItsN4A_9aqL10UQv_fg3WaSURR29X8eUj7niyCf_W3enaHsZg/exec"

            payload = {
                "participant_id": participant_name,
                "score": final_score,
            }

            response = requests.post(
                WEB_APP_URL,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )

            if response.status_code == 200:
                print("완료 기록이 성공적으로 제출(또는 업데이트)되었습니다!")
                submitted = True
            else:
                print(
                    f"🚨 완료 기록 제출에 실패했습니다. (서버 응답 코드: {response.status_code})"
                )
                print(f"   - 서버 메시지: {response.text}")

        except requests.exceptions.RequestException as e:
            print("🚨 완료 기록 제출에 실패했습니다. (네트워크 오류)")
            print(f"   - 오류 내용: {e}")
