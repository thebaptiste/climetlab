# (C) Copyright 2023 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#
import itertools
import logging
import math

LOG = logging.getLogger(__name__)

# class Cube:
#     def __init__(self, ds, *args, **kwargs):
#         assert args[-1] == "lon"
#         assert args[-2] == "lat"
#         args = args[:-2]
#         self._shape_spatial = ds[0].shape
#         self.field_cube = FieldCube(ds, *args, **kwargs)
#         self.shape = self.field_cube.shape + self._shape_spatial
#
#     def __getitem__(self, indexes):
#         item = self.field_cube[indexes[:-2]]
#         return item.to_numpy()[indexes[-2:]]
#
#     def to_numpy(self):
#         return self.ds.to_numpy(**kwargs).reshape(self.shape)


class FieldCube:
    def __init__(self, ds, *args, datetime="valid"):
        assert len(ds), f"No data in {ds}"

        assert datetime == "valid"
        self.datetime = datetime

        if len(args) == 1 and isinstance(args[0], (list, tuple)):
            args = [_ for _ in args[0]]

        self._field_shape = None
        print(f"* New FieldCube(args={args})")

        self.source = ds.order_by(*args)

        self.user_coords, self.internal_coords, self.slices = self._build_coords(
            self.source, args
        )

        print("---")
        print(f"{self.internal_coords=}")
        print(f"{self.user_coords=}")
        print("slices=", self.slices)

        self.internal_shape = tuple(len(v) for k, v in self.internal_coords.items())

        self.user_shape = []
        for s in self.slices:
            n = math.prod(self.internal_shape[s])
            self.user_shape.append(n)
        self.user_shape = tuple(self.user_shape)

        print(f"{self.user_shape=}")
        print(f"{self.internal_shape=}")

        self.user_ndim = len(self.user_shape)

        self.check_shape(self.internal_shape)
        self.check_shape(self.user_shape)
        print("extended_shape=", self.extended_user_shape)

    @property
    def field_shape(self):
        if self._field_shape is None:
            self._field_shape = self.source[0].shape
            print("fieldshape=", self._field_shape)
        return self._field_shape

    @property
    def extended_user_shape(self):
        return self.user_shape + self.field_shape

    @property
    def extended_internal_shape(self):
        return self.internal_shape + self.field_shape

    def __str__(self):
        content = ", ".join([f"{k}:{len(v)}" for k, v in self.user_coords.items()])
        return f"{self.__class__.__name__}({content} ({len(self.source)} fields))"

    def _transform_args(self, args):
        _args = []
        slices = []
        splits = []
        i = 0
        for a in args:
            lst = a.split("_")
            _args += lst
            slices.append(slice(i, i + len(lst)))
            splits.append(tuple(lst))
            i += len(lst)
        return _args, slices, splits

    def _build_coords(self, ds, args):
        # return a dict where the keys are from the args, in the right order
        # and the values are the coordinate.

        original_args = args
        args, slices, splits = self._transform_args(args)

        internal_coords = ds._all_coords(args)
        internal_coords = {k: internal_coords[k] for k in args}  # reordering
        assert math.prod(len(v) for v in internal_coords.values()) == len(ds)

        user_coords = {}
        for a, s in zip(original_args, splits):
            if len(s) == 1:
                user_coords[a] = internal_coords[a]
                continue

            lists = [internal_coords[k] for k in s]

            prod = list(_ for _ in itertools.product(*lists))
            user_coords[a] = ["_".join([str(x) for x in tupl]) for tupl in prod]

        user_coords = {k: user_coords[k] for k in original_args}  # reordering
        assert math.prod(len(v) for v in user_coords.values()) == len(ds), (
            user_coords,
            len(ds),
        )

        return user_coords, internal_coords, slices

    def squeeze(self):
        return self
        args = [k for k, v in self.coords.items() if len(v) > 1]
        if not args:
            # LOG.warn...
            return self
        return FieldCube(self.source, *args, datetime=self.datetime)

    def check_shape(self, shape):
        print("shape=", shape)
        if math.prod(shape) != len(self.source):
            msg = f"{shape} -> {math.prod(shape)} requested fields != {len(self.source)} available fields. "
            print("ERROR:", msg)
            raise ValueError(f"{msg}\n{self.source.availability}")

    def __getitem__(self, indexes):
        print("__getitem__", indexes)
        if isinstance(indexes, int):
            indexes = [indexes]

        if not isinstance(indexes, tuple):
            indexes = (indexes,)  # make tuple

        indexes = list(indexes)

        if indexes[-1] is Ellipsis:
            indexes.pop()

        while len(indexes) < self.user_ndim:
            indexes.append(slice(None, None, None))

        assert len(indexes) == len(self.user_shape), (indexes, self.user_shape)

        args = []
        selection_dict = {}

        names = self.user_coords.keys()
        assert len(names) == len(indexes), (names, indexes, self.user_coords)
        for i, name in zip(indexes, names):
            values = self.user_coords[name]
            if isinstance(i, int):
                if i >= len(values):
                    raise IndexError(f"index {i} out of range in {name} = {values}")
            selection_dict[name] = values[i]
            if isinstance(i, slice):
                args.append(name)

        if all(isinstance(x, int) for x in indexes):
            # # optimized version:
            # i = np.ravel_multi_index(indexes, self.internal_shape)
            # return self.source[i]
            # non-optimized version:
            _ds = self.source.sel(selection_dict)
            return _ds[0]

        print("s", selection_dict, args)
        _ds = self.source.sel(selection_dict)
        return FieldCube(_ds, *args)

    def to_numpy(self, **kwargs):
        return self.source.to_numpy(**kwargs).reshape(*self.extended_user_shape)

    def _names(self, coords, reading_chunks=None, **kwargs):
        if reading_chunks is None:
            reading_chunks = list(coords.keys())
        if isinstance(reading_chunks, (list, tuple)):
            assert all(isinstance(_, str) for _ in reading_chunks)
            reading_chunks = {k: len(coords[k]) for k in reading_chunks}

        for k, requested in reading_chunks.items():
            full_len = len(coords[k])
            assert full_len == requested, "only full chunks supported for now"

        names = list(coords[a] for a, _ in reading_chunks.items())

        return names

    def count(self, reading_chunks=None):
        names = self._names(reading_chunks=reading_chunks, coords=self.user_coords)
        return math.prod(len(lst) for lst in names)

    def iterate_cubelets(self, reading_chunks=None, **kwargs):
        names = self._names(reading_chunks=reading_chunks, coords=self.user_coords)
        indexes = list(range(0, len(lst)) for lst in names)

        # print('names:',names)
        # print('indexes:',indexes)
        return (
            Cubelet(self, i, indexes_names=n)
            for n, i in zip(itertools.product(*names), itertools.product(*indexes))
        )

    def chunking(self, **chunks):
        return True
        if not chunks:
            return True

        out = []
        for k, v in self.coords.items():
            if k in chunks:
                out.append(chunks[k])
            else:
                out.append(len(v))
        out += list(self.field_shape)
        return out


class Cubelet:
    def __init__(self, cube, indexes, indexes_names=None):
        self.owner = cube
        assert all(isinstance(_, int) for _ in indexes), indexes
        self.indexes = indexes
        self.index_names = indexes_names
        print(self)

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.indexes},index_names={self.index_names})"
        )

    @property
    def extended_icoords(self):
        return self.indexes

    def to_numpy(self, **kwargs):
        return self.owner[self.indexes].to_numpy(**kwargs)
