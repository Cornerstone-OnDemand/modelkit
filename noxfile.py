import nox


@nox.session(python=["3.8", "3.9", "3.10", "3.11"])
def tests(session):
    # Install deps and the package itself.
    session.install(".[cli,api,assets-gcs,assets-s3,assets-az]")
    session.install("-r", "requirements-dev.txt")

    session.run("pytest", "--junitxml=junit.xml", "-s")


@nox.session(python=["3.8", "3.9", "3.10", "3.11"])
def coverage(session):
    # Install deps and the package itself.
    session.install(".[cli,api,tensorflow,assets-s3,assets-gcs,assets-az]")
    session.install("-r", "requirements-dev.txt")

    session.run("coverage", "run", "-m", "pytest", "--junitxml=junit.xml", "-s")
    session.run("coverage", "report", "-m")
    session.run("coverage", "xml")
    session.run("coverage", "html", "-d", "docs/coverage")
