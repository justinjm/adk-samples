"""
delete_bq_models.py

Deletes all BigQuery ML model objects within a specified dataset.

Usage:
    python delete_bq_models.py --project YOUR_PROJECT_ID --dataset YOUR_DATASET_ID
    python delete_bq_models.py --project YOUR_PROJECT_ID --dataset YOUR_DATASET_ID --dry-run
"""

import argparse
import sys

from google.cloud import bigquery
from google.api_core.exceptions import NotFound


def list_models(client: bigquery.Client, project: str, dataset: str) -> list:
    """List all models in the given dataset."""
    dataset_ref = bigquery.DatasetReference(project, dataset)
    models = list(client.list_models(dataset_ref))
    return models


def delete_all_models(
    client: bigquery.Client,
    project: str,
    dataset: str,
    dry_run: bool = False,
) -> None:
    """Delete all BigQuery ML models in the specified dataset."""
    print(f"\nProject : {project}")
    print(f"Dataset : {dataset}")
    print(f"Dry run : {dry_run}\n")

    models = list_models(client, project, dataset)

    if not models:
        print("No models found in the dataset. Nothing to delete.")
        return

    print(f"Found {len(models)} model(s):\n")
    for model in models:
        print(f"  - {model.model_id}")

    if dry_run:
        print("\n[DRY RUN] No models were deleted.")
        return

    # Confirm deletion interactively unless stdin is not a TTY
    if sys.stdin.isatty():
        confirm = input(
            f"\nAre you sure you want to delete all {len(models)} model(s)? [y/N]: "
        ).strip().lower()
        if confirm != "y":
            print("Aborted. No models were deleted.")
            return

    print("\nDeleting models...")
    deleted = 0
    failed = 0

    for model in models:
        model_ref = client.get_model(
            bigquery.ModelReference.from_string(
                f"{project}.{dataset}.{model.model_id}"
            )
        )
        try:
            client.delete_model(model_ref)
            print(f"  ✓ Deleted: {model.model_id}")
            deleted += 1
        except NotFound:
            print(f"  ✗ Not found (already deleted?): {model.model_id}")
            failed += 1
        except Exception as e:  # pylint: disable=broad-except
            print(f"  ✗ Error deleting {model.model_id}: {e}")
            failed += 1

    print(f"\nDone. Deleted: {deleted}, Failed: {failed}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Delete all BigQuery ML models within a specified dataset."
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Google Cloud project ID",
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help="BigQuery dataset ID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="List models without deleting them",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = bigquery.Client(project=args.project)
    delete_all_models(
        client=client,
        project=args.project,
        dataset=args.dataset,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
