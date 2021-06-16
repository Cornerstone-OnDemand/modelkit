import nox


@nox.session(python=["3.7"])
def test(session):
    # Install deps and the package itself.
    session.install("-r", "requirements-dev.txt")

    session.run(
        "pytest"
    )

@nox.session(python=["3.7"])
def coverage(session):
    # Install deps and the package itself.
    session.install("-r", "requirements-optional.txt")

    session.run(
        "coverage",
        "run",
        "-m",
        "pytest"
    )
    session.run("coverage", "report", "-m")
    session.run("coverage", "xml")
