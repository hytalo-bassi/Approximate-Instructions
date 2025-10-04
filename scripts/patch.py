import os
from typing import Optional
import argparse


def patch_file(
    filepath: str,
    patch: str,
    position_string: str,
    after: bool = True,
    condition_string: Optional[str] = None,
    breaklines: bool = True,
) -> bool:
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found")
        return False

    with open(filepath, "r") as f:
        content = f.read()

    if condition_string and condition_string not in content:
        print(f"Error: {condition_string} not found!")
        return False
    else:
        patch = f"\n{patch}\n" if breaklines else patch
        insertion_point = content.find(position_string)
        if insertion_point != -1:
            last_index = (
                insertion_point + len(position_string) if after else insertion_point
            )
            new_content = content[:last_index] + patch + content[last_index:]

            with open(filepath, "w") as f:
                f.write(new_content)
            return True

    print(f"Error: Could not find insertion point in {filepath}")
    return False


def create_parser():
    parser = argparse.ArgumentParser(
        description="Pattern file patcher",
        epilog="""
Examples
    %(prog)s /file/path "new_content" "pattern to be found"
    %(prog)s /file/path "new_content" "pattern to be found" --after
    %(prog)s /file/path "new_content" "pattern to be found" "file has this pattern"
        """,
    )

    parser.add_argument("path", help="Path to file you want to patch")
    parser.add_argument("patch", help="The content you want to patch")
    parser.add_argument(
        "pattern",
        help="Searches for this pattern in file. It's also used to know where to put the patch",
    )

    parser.add_argument(
        "contains_pattern",
        nargs="?",
        default=None,
        help="Check if file have some specific pattern",
    )
    parser.add_argument(
        "--after",
        "-a",
        action="store_true",
        help="Places modifications after pattern found",
    )
    parser.add_argument(
        "--breaklines",
        "-b",
        action="store_false",
        help="Add breaklines both to beggining and ending of the patch",
    )

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    filepath = args.path
    patch = args.patch
    pattern = args.pattern
    after = args.after
    contains_pattern = args.contains_pattern
    breaklines = args.breaklines

    patch_file(filepath, patch, pattern, after, contains_pattern, breaklines)


if __name__ == "__main__":
    main()
