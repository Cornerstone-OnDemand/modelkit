import nox


@nox.session(python=["3.7"])
def test(session):
    # Install deps and the package itself.
    session.install("-r", "requirements-dev.txt")

    session.run(
        "coverage",
        "run",
        "-m",
        "pytest",
        env={"PYTHONWARNINGS": "always::DeprecationWarning"},
    )
    session.run("coverage", "report", "-m")
    session.run("coverage", "xml")
