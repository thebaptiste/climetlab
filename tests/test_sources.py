#!/usr/bin/env python3

# (C) Copyright 2020 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import sys
from climetlab import load_source, source
from .utils import is_package_installed
import pytest


def test_file_source_grib():
    s = load_source("file", "docs/examples/test.grib")
    assert len(s) == 2


def test_file_source_netcdf():
    s = load_source("file", "docs/examples/test.nc")
    assert len(s) == 2


@pytest.mark.skipif(sys.version_info < (3, 7), reason="Version 3.7 or greater needed")
def test_file_source_shortcut():
    s = source.file("docs/examples/test.grib")
    assert len(s) == 2


S3_URL = "https://storage.ecmwf.europeanweather.cloud/s2s-ai-competition/data/fixtures"


@pytest.mark.skipif(
    not is_package_installed(["zarr", "s3fs"]), reason="Zarr or S3FS not installed"
)
def test_zarr_source_1():
    source = load_source(
        "zarr-s3",
        # f"{S3_URL}/rt-20200102.zarr",
        f"{S3_URL}/0.1.20/zarr/mini-rt-20200102.zarr",
    )
    ds = source.to_xarray()
    assert len(ds.forecast_time) == 1


@pytest.mark.skipif(
    not is_package_installed(["zarr", "s3fs"]), reason="Zarr or S3FS not installed"
)
def test_zarr_source_2():
    from climetlab.utils.dates import to_datetime_list
    import datetime

    source = load_source(
        "zarr-s3",
        [
            f"{S3_URL}/0.1.20/zarr/mini-rt-20200109.zarr",
            f"{S3_URL}/0.1.20/zarr/mini-rt-20200102.zarr",
        ],
    )

    ds = source.to_xarray()
    assert len(ds.forecast_time) == 2

    dates = to_datetime_list(ds.forecast_time)
    assert dates[0] == datetime.datetime(2020, 1, 2)
    assert dates[1] == datetime.datetime(2020, 1, 9)

    dates = to_datetime_list(ds.forecast_time.values)
    assert dates[0] == datetime.datetime(2020, 1, 2)
    assert dates[1] == datetime.datetime(2020, 1, 9)


@pytest.mark.skipif(
    not is_package_installed(["zarr", "s3fs"]), reason="Zarr or S3FS not installed"
)
def test_zarr_source_3():
    from climetlab.utils.dates import to_datetime_list
    import datetime

    source = load_source(
        "zarr-s3",
        [
            f"{S3_URL}/0.1.20/zarr/mini-hc-20200109.zarr",
            f"{S3_URL}/0.1.20/zarr/mini-hc-20200102.zarr",
        ],
    )
    ds = source.to_xarray()
    assert len(ds.forecast_time) == 8

    dates = to_datetime_list(ds.forecast_time)
    assert dates[0] == datetime.datetime(2000, 1, 2)
    assert dates[1] == datetime.datetime(2000, 1, 9)
    assert dates[2] == datetime.datetime(2001, 1, 2)
    assert dates[3] == datetime.datetime(2001, 1, 9)

    dates = to_datetime_list(ds.forecast_time.values)
    assert dates[0] == datetime.datetime(2000, 1, 2)
    assert dates[1] == datetime.datetime(2000, 1, 9)
    assert dates[2] == datetime.datetime(2001, 1, 2)
    assert dates[3] == datetime.datetime(2001, 1, 9)


if __name__ == "__main__":
    test_zarr_source_2()
