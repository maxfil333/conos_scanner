import re
import json
from pathlib import Path
from termcolor import colored
import Levenshtein


def read_json(path):
    with open(path, mode="r", encoding="utf-8") as file:
        return json.load(file)


def highlight_diff(gt: str, pred: str) -> str:
    """Выделение различий в двух строках.

    Args:
        gt: Ground truth text.
        pred: Prediction text.

    Returns:
        Срока, в которой с помощью ansi-кодов отмечены отличия в текстах:
            - красным цветом - добавленные или замененные символы
    """
    opcodes = Levenshtein.opcodes(gt, pred)
    result = []
    for tag, i1, i2, j1, j2 in opcodes:
        gt_fragment = gt[i1:i2]
        pred_fragment = pred[j1:j2]

        if tag == 'equal':
            result.append(pred_fragment)

        elif tag in ('replace', 'insert'):
            result.append(colored(pred_fragment, 'red'))

    return ''.join(result)


def compare_dicts(ground_truth, predictions, mismatch_count=0, total_count=0):
    """Сравнивает рекурсивно два словаря."""
    for key in ground_truth.keys():
        ground_truth_value, prediction_value = ground_truth.get(key), predictions.get(key)

        if isinstance(ground_truth_value, dict) and isinstance(prediction_value, dict):
            mismatch_count, total_count = compare_dicts(ground_truth_value, prediction_value, mismatch_count,
                                                        total_count)
        elif isinstance(ground_truth_value, list) and isinstance(prediction_value, list):
            for gt_item, pred_item in zip(ground_truth_value, prediction_value):
                mismatch_count, total_count = compare_dicts(gt_item, pred_item, mismatch_count, total_count)
        else:
            total_count += 1
            if ground_truth_value != prediction_value:
                mismatch_count += 1
                print(f"{key}")
                print(f"  - {colored('GT:  ', attrs=['bold'])} {ground_truth_value}")
                print(f"  - {colored('Pred:', attrs=['bold'])} {highlight_diff(ground_truth_value, prediction_value)}")

    return mismatch_count, total_count


def main():
    ground_truth_paths = Path("valid/ground_truth").rglob("*.json")
    mismatches_global, total_global = 0, 0
    for idx, gt_path in enumerate(ground_truth_paths):
        print(f"{colored(f'  {idx}  '.center(80, '='), attrs=['bold'])}")
        print(f"{colored(gt_path.name.center(80, ' '), attrs=['bold'])}")
        # print("=" * 80)
        pred_path = gt_path.parent.parent / "predictions" / gt_path.name
        if pred_path.exists():
            gt_data = read_json(gt_path)
            pred_data = read_json(pred_path)

            mismatch_count, total_count = compare_dicts(gt_data, pred_data)
            mismatches_global += mismatch_count
            total_global += total_count

            if mismatch_count == 0:
                print(colored("ПОЛНОЕ СОВПАДЕНИЕ!", "green", attrs=["bold"]))
            print()

    # print("\n")
    print(f"{colored('  RESULTS  '.center(80, '='), attrs=['bold'])}")
    print(f"Accuracy: {(total_global - mismatches_global) / total_global:.4f}")


if __name__ == "__main__":
    main()
