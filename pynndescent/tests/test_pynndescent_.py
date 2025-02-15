import os
import io
import re
from contextlib import redirect_stdout

from nose.tools import assert_greater_equal, assert_true, assert_equal

import numpy as np
from scipy import sparse
from sklearn.neighbors import KDTree
from sklearn.preprocessing import normalize

from pynndescent import NNDescent, PyNNDescentTransformer

np.random.seed(42)
spatial_data = np.random.randn(10, 20)
spatial_data = np.vstack(
    [spatial_data, np.zeros((2, 20))]
)  # Add some all zero data for corner case test

nn_data = np.random.uniform(0, 1, size=(1000, 5))
nn_data = np.vstack(
    [nn_data, np.zeros((2, 5))]
)  # Add some all zero data for corner case test
# for_sparse_nn_data = np.random.uniform(0, 1, size=(1002, 500))
# binary_nn_data = np.random.choice(a=[False, True], size=(1000, 500), p=[0.1, 1 - 0.1])
# binary_nn_data = np.vstack(
#     [binary_nn_data, np.zeros((2, 500))]
# )  # Add some all zero data for corner case test
# sparse_nn_data = sparse.csr_matrix(for_sparse_nn_data * binary_nn_data)
sparse_nn_data = sparse.random(1000, 50, density=0.5, format="csr")
# sparse_nn_data = sparse.csr_matrix(nn_data)


def test_nn_descent_neighbor_accuracy():
    knn_indices, _ = NNDescent(
        nn_data, "euclidean", {}, 10, random_state=np.random
    )._neighbor_graph

    tree = KDTree(nn_data)
    true_indices = tree.query(nn_data, 10, return_distance=False)

    num_correct = 0.0
    for i in range(nn_data.shape[0]):
        num_correct += np.sum(np.in1d(true_indices[i], knn_indices[i]))

    percent_correct = num_correct / (nn_data.shape[0] * 10)
    assert_greater_equal(
        percent_correct,
        0.98,
        "NN-descent did not get 99% " "accuracy on nearest neighbors",
    )


def test_angular_nn_descent_neighbor_accuracy():
    knn_indices, _ = NNDescent(
        nn_data, "cosine", {}, 10, random_state=np.random
    )._neighbor_graph

    angular_data = normalize(nn_data, norm="l2")
    tree = KDTree(angular_data)
    true_indices = tree.query(angular_data, 10, return_distance=False)

    num_correct = 0.0
    for i in range(nn_data.shape[0]):
        num_correct += np.sum(np.in1d(true_indices[i], knn_indices[i]))

    percent_correct = num_correct / (nn_data.shape[0] * 10)
    assert_greater_equal(
        percent_correct,
        0.98,
        "NN-descent did not get 99% " "accuracy on nearest neighbors",
    )


def test_sparse_nn_descent_neighbor_accuracy():
    knn_indices, _ = NNDescent(
        sparse_nn_data, "euclidean", n_neighbors=20, random_state=np.random
    )._neighbor_graph

    tree = KDTree(sparse_nn_data.toarray())
    true_indices = tree.query(sparse_nn_data.toarray(), 10, return_distance=False)

    num_correct = 0.0
    for i in range(sparse_nn_data.shape[0]):
        num_correct += np.sum(np.in1d(true_indices[i], knn_indices[i]))

    percent_correct = num_correct / (sparse_nn_data.shape[0] * 10)
    assert_greater_equal(
        percent_correct,
        0.85,
        "Sparse NN-descent did not get 95% " "accuracy on nearest neighbors",
    )


def test_sparse_angular_nn_descent_neighbor_accuracy():
    knn_indices, _ = NNDescent(
        sparse_nn_data, "cosine", {}, 20, random_state=np.random
    )._neighbor_graph

    angular_data = normalize(sparse_nn_data, norm="l2").toarray()
    tree = KDTree(angular_data)
    true_indices = tree.query(angular_data, 10, return_distance=False)

    num_correct = 0.0
    for i in range(sparse_nn_data.shape[0]):
        num_correct += np.sum(np.in1d(true_indices[i], knn_indices[i]))

    percent_correct = num_correct / (sparse_nn_data.shape[0] * 10)
    assert_greater_equal(
        percent_correct,
        0.85,
        "Sparse angular NN-descent did not get 98% " "accuracy on nearest neighbors",
    )


def test_nn_descent_query_accuracy():
    nnd = NNDescent(nn_data[200:], "euclidean", n_neighbors=10, random_state=np.random)
    knn_indices, _ = nnd.query(nn_data[:200], k=10)

    tree = KDTree(nn_data[200:])
    true_indices = tree.query(nn_data[:200], 10, return_distance=False)

    num_correct = 0.0
    for i in range(true_indices.shape[0]):
        num_correct += np.sum(np.in1d(true_indices[i], knn_indices[i]))

    percent_correct = num_correct / (true_indices.shape[0] * 10)
    assert_greater_equal(
        percent_correct,
        0.99,
        "NN-descent query did not get 99% " "accuracy on nearest neighbors",
    )


def test_sparse_nn_descent_query_accuracy():
    nnd = NNDescent(
        sparse_nn_data[200:], "euclidean", n_neighbors=10, random_state=np.random
    )
    knn_indices, _ = nnd.query(sparse_nn_data[:200], k=10)

    tree = KDTree(sparse_nn_data[200:].toarray())
    true_indices = tree.query(sparse_nn_data[:200].toarray(), 10, return_distance=False)

    num_correct = 0.0
    for i in range(true_indices.shape[0]):
        num_correct += np.sum(np.in1d(true_indices[i], knn_indices[i]))

    percent_correct = num_correct / (true_indices.shape[0] * 10)
    assert_greater_equal(
        percent_correct,
        0.95,
        "Sparse NN-descent query did not get 97% " "accuracy on nearest neighbors",
    )


def test_transformer_equivalence():
    N_NEIGHBORS = 15
    QUEUE_SIZE = 5.0
    train = nn_data[:400]
    test = nn_data[:200]

    nnd = NNDescent(data=train, n_neighbors=N_NEIGHBORS, random_state=42)
    indices, dists = nnd.query(test, k=N_NEIGHBORS, queue_size=QUEUE_SIZE)
    sort_idx = np.argsort(indices, axis=1)
    indices_sorted = np.vstack(
        [indices[i, sort_idx[i]] for i in range(sort_idx.shape[0])]
    )
    dists_sorted = np.vstack([dists[i, sort_idx[i]] for i in range(sort_idx.shape[0])])

    transformer = PyNNDescentTransformer(
        n_neighbors=N_NEIGHBORS, search_queue_size=QUEUE_SIZE, random_state=42
    ).fit(train)
    Xt = transformer.transform(test).sorted_indices()

    assert np.all(Xt.indices == indices_sorted.flat)
    assert np.allclose(Xt.data, dists_sorted.flat)


def test_random_state_none():
    knn_indices, _ = NNDescent(
        nn_data, "euclidean", {}, 10, random_state=None
    )._neighbor_graph

    tree = KDTree(nn_data)
    true_indices = tree.query(nn_data, 10, return_distance=False)

    num_correct = 0.0
    for i in range(nn_data.shape[0]):
        num_correct += np.sum(np.in1d(true_indices[i], knn_indices[i]))

    percent_correct = num_correct / (spatial_data.shape[0] * 10)
    assert_greater_equal(
        percent_correct,
        0.99,
        "NN-descent did not get 99% " "accuracy on nearest neighbors",
    )


def test_deterministic():
    seed = np.random.RandomState(42)

    x1 = seed.normal(0, 100, (1000, 50))
    x2 = seed.normal(0, 100, (1000, 50))

    index1 = NNDescent(x1, random_state=np.random.RandomState(42))
    neighbors1, distances1 = index1.query(x2)

    index2 = NNDescent(x1, random_state=np.random.RandomState(42))
    neighbors2, distances2 = index2.query(x2)

    np.testing.assert_equal(neighbors1, neighbors2)
    np.testing.assert_equal(distances1, distances2)


# This tests a recursion error on cosine metric reported at:
# https://github.com/lmcinnes/umap/issues/99
# data used is a cut-down version of that provided by @scharron
# It contains lots of all-zero vectors and some other duplicates
def test_rp_trees_should_not_stack_overflow_with_duplicate_data():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(this_dir, "test_data/cosine_hang.npy")
    data = np.load(data_path)

    n_neighbors = 10
    knn_indices, _ = NNDescent(
        data, "cosine", {}, n_neighbors, random_state=np.random, n_trees=20
    )._neighbor_graph

    for i in range(data.shape[0]):
        assert_equal(
            len(knn_indices[i]),
            len(np.unique(knn_indices[i])),
            "Duplicate indices in knn graph",
        )


def test_deduplicated_data_behaves_normally():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(this_dir, "test_data/cosine_hang.npy")
    data = np.unique(np.load(data_path), axis=0)
    data = data[~np.all(data == 0, axis=1)]
    data = data[:1000]

    n_neighbors = 10
    knn_indices, _ = NNDescent(
        data, "cosine", {}, n_neighbors, random_state=np.random, n_trees=20
    )._neighbor_graph

    for i in range(data.shape[0]):
        assert_equal(
            len(knn_indices[i]),
            len(np.unique(knn_indices[i])),
            "Duplicate indices in knn graph",
        )

    angular_data = normalize(data, norm="l2")
    tree = KDTree(angular_data)
    true_indices = tree.query(angular_data, n_neighbors, return_distance=False)

    num_correct = 0
    for i in range(data.shape[0]):
        num_correct += np.sum(np.in1d(true_indices[i], knn_indices[i]))

    proportion_correct = num_correct / (data.shape[0] * n_neighbors)
    assert_greater_equal(
        proportion_correct,
        0.95,
        "NN-descent did not get 95%" " accuracy on nearest neighbors",
    )


def test_output_when_verbose_is_true():
    out = io.StringIO()
    with redirect_stdout(out):
        _ = NNDescent(
            data=spatial_data,
            metric="euclidean",
            metric_kwds={},
            n_neighbors=4,
            random_state=np.random,
            n_trees=5,
            n_iters=2,
            verbose=True,
        )
    output = out.getvalue()
    assert_true(re.match("^.*5 trees", output, re.DOTALL))
    assert_true(re.match("^.*2 iterations", output, re.DOTALL))


def test_no_output_when_verbose_is_false():
    out = io.StringIO()
    with redirect_stdout(out):
        _ = NNDescent(
            data=spatial_data,
            metric="euclidean",
            metric_kwds={},
            n_neighbors=4,
            random_state=np.random,
            n_trees=5,
            n_iters=2,
            verbose=False,
        )
    output = out.getvalue().strip()
    assert_equal(len(output), 0)


# same as the previous two test, but this time using the PyNNDescentTransformer
# interface
def test_transformer_output_when_verbose_is_true():
    out = io.StringIO()
    with redirect_stdout(out):
        _ = PyNNDescentTransformer(
            n_neighbors=4,
            metric="euclidean",
            metric_kwds={},
            random_state=np.random,
            n_trees=5,
            n_iters=2,
            verbose=True,
        ).fit_transform(spatial_data)
    output = out.getvalue()
    assert_true(re.match("^.*5 trees", output, re.DOTALL))
    assert_true(re.match("^.*2 iterations", output, re.DOTALL))


def test_transformer_output_when_verbose_is_false():
    out = io.StringIO()
    with redirect_stdout(out):
        _ = PyNNDescentTransformer(
            n_neighbors=4,
            metric="euclidean",
            metric_kwds={},
            random_state=np.random,
            n_trees=5,
            n_iters=2,
            verbose=False,
        ).fit_transform(spatial_data)
    output = out.getvalue().strip()
    assert_equal(len(output), 0)
