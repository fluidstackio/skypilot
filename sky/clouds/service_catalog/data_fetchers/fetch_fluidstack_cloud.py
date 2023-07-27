"""A script that generates the Lambda Cloud catalog.

Usage:
    python fetch_lambda_cloud.py [-h] [--api-key API_KEY]
                                 [--api-key-path API_KEY_PATH]

If neither --api-key nor --api-key-path are provided, this script will parse
`~/.lambda/lambda_keys` to look for Lambda API key.
"""
import argparse
import csv
import json
import os
import requests
import json
from typing import Optional, List
from sky.clouds.service_catalog import constants

ENDPOINT = "https://console.fluidstack.io/api/plans"
DEFAULT_FLUIDSTACK_API_KEY_PATH = os.path.expanduser("~/.fluidstack/fluidstack_api_key")
DEFAULT_FLUIDSTACK_API_TOKEN_PATH = os.path.expanduser(
    "~/.fluidstack/fluidstack_api_token"
)


GPU_TO_MEMORY = {
    "A100": 40960,
    "A100-80GB": 81920,
    "A6000": 49152,
    "A10": 24576,
    "RTX6000": 24576,
    "V100": 16384,
    "H100": 81920,
}
GPU_MAP = {
    "A100_PCIE_40GB": "A100",
    "T4": "T4",
    "Tesla_V100_PCIE": "V100",
    "A10": "A10",
    "A100_PCIE_80GB": "A100-80GB",
}


def get_regions(plans: List) -> dict:
    """Return a list of regions where the plan is available."""
    regions = {}
    for plan in plans:
        for region in plan.get("regions", []):
            regions[region["description"]] = region["id"]
    return regions


def create_catalog(output_dir: str) -> None:
    response = requests.get(ENDPOINT)
    plans = response.json()
    plans = [
        plan
        for plan in plans
        if plan["minimum_commitment"] == "hourly"
        and plan["type"] in ["preconfigured"]
        and plan["gpu_type"] != "NO GPU"
    ]
    # regions = get_regions(plans)
    # with open(os.path.join(output_dir, "regions.json"), mode="w") as f:
    #     json.dump(regions, f)

    with open(os.path.join(output_dir, "vms.csv"), mode="w") as f:
        writer = csv.writer(f, delimiter=",", quotechar='"')
        writer.writerow(
            [
                "InstanceType",
                "AcceleratorName",
                "AcceleratorCount",
                "vCPUs",
                "MemoryGiB",
                "Price",
                "Region",
                "GpuInfo",
                "SpotPrice",
            ]
        )

        for plan in plans:
            gpu = plan["gpu_type"].replace("_", "-")
            gpu_cnt = float(plan["configuration"]["gpu_count"])
            vcpus = float(plan["configuration"]["core_count"])
            mem = float(plan["configuration"]["ram"])
            price = float(plan["price"]["hourly"]) * gpu_cnt
            gpuinfo = {
                "Gpus": [
                    {
                        "Name": gpu,
                        "Manufacturer": "NVIDIA",
                        "Count": gpu_cnt,
                        "MemoryInfo": {"SizeInMiB": 0},
                    }
                ],
                "TotalGpuMemoryInMiB": 0,
            }
            gpuinfo = json.dumps(gpuinfo).replace(
                '"', "'"
            )  # pylint: disable=invalid-string-quote
            for r in plan.get("regions", []):
                writer.writerow(
                    [
                        plan["plan_id"],
                        gpu,
                        gpu_cnt,
                        vcpus,
                        mem,
                        price,
                        r["description"],
                        gpuinfo,
                        "",
                    ]
                )


# def get_api_keys(cmdline_args: argparse.Namespace) -> str:
#     """Get Fluidstack API key from cmdline or DEFAULT_FLUIDSTACK_API*."""
#     api_key, api_token = None, None
#     if cmdline_args.api_key_path is not None and cmdline_args.api_token_path:
#         with open(cmdline_args.api_key_path, mode="r") as f:
#             api_key = f.read().strip()
#         with open(cmdline_args.api_token_path, mode="r") as f:
#             api_token = f.read().strip()
#     assert api_key is not None
#     assert api_token is not None
#     return api_key, api_token


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    _CATALOG_DIR = os.path.join(
        constants.LOCAL_CATALOG_DIR, constants.CATALOG_SCHEMA_VERSION
    )
    catalog_dir = os.path.join(_CATALOG_DIR, "fluidstack")
    os.makedirs(catalog_dir, exist_ok=True)
    create_catalog(catalog_dir)
    print("Fluidstack Cloud catalog saved to fluidstack/vms.csv")
