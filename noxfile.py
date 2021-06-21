import nox


@nox.session(python=["3.7"])
def test(session):
    # Install deps and the package itself.
    session.install("-r", "requirements-dev.txt")

    session.run("pytest", "--junitxml=junit.xml")
    session.install("genbadge[tests]")
    session.run("genbadge", "tests", "-i", "junit.xml", "-o", "docs/badges/tests.svg")


@nox.session(python=["3.7"])
def coverage(session):
    # Install deps and the package itself.
    session.install("-r", "requirements-optional.txt")

    session.run("coverage", "run", "-m", "pytest")
    session.run("coverage", "report", "-m")
    session.install("genbadge[coverage]")
    session.run(
        "genbadge",
        "coverage",
        "-i",
        "coverage.xml",
        "-o",
        "docs/badges/coverage.svg",
    )
