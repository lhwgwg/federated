load("@rules_python//python:defs.bzl", "py_library", "py_test")

licenses(["notice"])

py_library(
    name = "models",
    srcs = ["__init__.py"],
    srcs_version = "PY3",
    visibility = ["//tensorflow_federated/python/learning:learning_packages"],
    deps = [
        ":functional",
        ":serialization",
    ],
)

py_library(
    name = "functional",
    srcs = ["functional.py"],
    srcs_version = "PY3",
    visibility = ["//tensorflow_federated/python/learning:learning_packages"],
    deps = [
        "//tensorflow_federated/python/common_libs:py_typecheck",
        "//tensorflow_federated/python/learning:model",
        "//tensorflow_federated/python/learning/metrics:finalizer",
        "//tensorflow_federated/python/tensorflow_libs:variable_utils",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "functional_test",
    srcs = ["functional_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":functional",
        "//tensorflow_federated/python/core/backends/native:execution_contexts",
        "//tensorflow_federated/python/core/impl/types:type_conversions",
        "//tensorflow_federated/python/learning:model",
        "//tensorflow_federated/python/learning/metrics:aggregator",
        "//tensorflow_federated/python/tensorflow_libs:variable_utils",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "serialization",
    srcs = ["serialization.py"],
    srcs_version = "PY3",
    deps = [
        ":functional",
        "//tensorflow_federated/proto/v0:computation_py_pb2",
        "//tensorflow_federated/python/common_libs:py_typecheck",
        "//tensorflow_federated/python/common_libs:structure",
        "//tensorflow_federated/python/core/api:computations",
        "//tensorflow_federated/python/core/impl/computation:computation_serialization",
        "//tensorflow_federated/python/core/impl/types:computation_types",
        "//tensorflow_federated/python/core/impl/types:type_conversions",
        "//tensorflow_federated/python/core/impl/types:type_serialization",
        "//tensorflow_federated/python/learning:model",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "serialization_test",
    srcs = ["serialization_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":functional",
        ":serialization",
        ":test_models",
        "//tensorflow_federated/python/core/api:computations",
        "//tensorflow_federated/python/core/backends/native:execution_contexts",
        "//tensorflow_federated/python/core/impl/types:computation_types",
        "//tensorflow_federated/python/core/impl/types:type_conversions",
        "//tensorflow_federated/python/core/impl/types:type_serialization",
        "//tensorflow_federated/python/core/impl/types:type_test_utils",
        "//tensorflow_federated/python/learning:federated_averaging",
        "//tensorflow_federated/python/learning:keras_utils",
        "//tensorflow_federated/python/learning:model",
        "//tensorflow_federated/python/learning:model_examples",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "test_models",
    testonly = True,
    srcs = ["test_models.py"],
    visibility = ["//tensorflow_federated/python/learning:learning_packages"],
    deps = [
        ":functional",
        "//tensorflow_federated/python/learning:model",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)
