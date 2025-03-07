load("@rules_python//python:defs.bzl", "py_library", "py_test")

package(default_visibility = [
    ":optimizers_packages",
    "//tensorflow_federated/python/learning:learning_visibility",
    "//tensorflow_federated/python/learning/algorithms:algorithms_packages",
    "//tensorflow_federated/python/learning/reconstruction:reconstruction_packages",
    "//tensorflow_federated/python/learning/templates:templates_packages",

    # TODO(b/151441025): This visibility is temporary and can be removed once
    # the dependencies between `tff.learning` and `tff.learning.framework` are
    # cleaned up.
    "//tensorflow_federated/python/learning/framework:framework_packages",
    "//tensorflow_federated/python/learning:__pkg__",
])

package_group(
    name = "optimizers_packages",
    packages = ["//tensorflow_federated/python/learning/optimizers/..."],
)

licenses(["notice"])

py_library(
    name = "adagrad",
    srcs = ["adagrad.py"],
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        "//tensorflow_federated/python/common_libs:py_typecheck",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "adagrad_test",
    srcs = ["adagrad_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":adagrad",
        ":optimizer",
        ":optimizer_test_utils",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "adam",
    srcs = ["adam.py"],
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        "//tensorflow_federated/python/common_libs:py_typecheck",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "adam_test",
    srcs = ["adam_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":adam",
        ":optimizer",
        ":optimizer_test_utils",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "optimizers",
    srcs = ["__init__.py"],
    srcs_version = "PY3",
    visibility = ["//tensorflow_federated/python/learning:__pkg__"],
    deps = [
        ":adagrad",
        ":adam",
        ":optimizer",
        ":rmsprop",
        ":scheduling",
        ":sgdm",
        ":yogi",
    ],
)

py_library(
    name = "keras_optimizer",
    srcs = ["keras_optimizer.py"],
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "keras_optimizer_test",
    srcs = ["keras_optimizer_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":keras_optimizer",
        ":optimizer",
        ":optimizer_test_utils",
        ":sgdm",
        "//tensorflow_federated/python/core/api:computations",
        "//tensorflow_federated/python/core/backends/native:execution_contexts",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "integration_test",
    srcs = ["integration_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":adagrad",
        ":adam",
        ":rmsprop",
        ":scheduling",
        ":sgdm",
        ":yogi",
        "//tensorflow_federated/python/core/api:computations",
        "//tensorflow_federated/python/core/backends/native:execution_contexts",
        "//tensorflow_federated/python/core/impl/federated_context:intrinsics",
        "//tensorflow_federated/python/core/impl/types:computation_types",
        "//tensorflow_federated/python/core/impl/types:placements",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "optimizer",
    srcs = ["optimizer.py"],
    srcs_version = "PY3",
    deps = ["@org_tensorflow//tensorflow:tensorflow_py"],
)

py_test(
    name = "optimizer_test",
    srcs = ["optimizer_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "optimizer_test_utils",
    testonly = True,
    srcs = ["optimizer_test_utils.py"],
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "optimizer_test_utils_test",
    srcs = ["optimizer_test_utils_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":optimizer_test_utils",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "rmsprop",
    srcs = ["rmsprop.py"],
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        "//tensorflow_federated/python/common_libs:py_typecheck",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "rmsprop_test",
    srcs = ["rmsprop_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        ":optimizer_test_utils",
        ":rmsprop",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "scheduling",
    srcs = ["scheduling.py"],
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        "//tensorflow_federated/python/common_libs:py_typecheck",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "scheduling_test",
    srcs = ["scheduling_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":adagrad",
        ":adam",
        ":optimizer",
        ":rmsprop",
        ":scheduling",
        ":sgdm",
        ":yogi",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "sgdm",
    srcs = ["sgdm.py"],
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        "//tensorflow_federated/python/common_libs:py_typecheck",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "sgdm_test",
    srcs = ["sgdm_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        ":optimizer_test_utils",
        ":sgdm",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_library(
    name = "yogi",
    srcs = ["yogi.py"],
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        "//tensorflow_federated/python/common_libs:py_typecheck",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)

py_test(
    name = "yogi_test",
    srcs = ["yogi_test.py"],
    python_version = "PY3",
    srcs_version = "PY3",
    deps = [
        ":optimizer",
        ":optimizer_test_utils",
        ":yogi",
        "@absl_py//absl/testing:parameterized",
        "@org_tensorflow//tensorflow:tensorflow_py",
    ],
)
