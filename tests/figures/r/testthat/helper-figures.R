repo_root <- normalizePath(file.path(dirname(testthat::test_path()), "..", "..", "..", ".."), winslash = "/", mustWork = TRUE)
options(manuscript.figure.repo_root = repo_root)
