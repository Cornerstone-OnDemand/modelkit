import nox


@nox.session(python=["3.7", "3.8", "3.9"])
def test(session):
    # Install deps and the package itself.
    session.install("-r", "requirements-dev.txt")

    session.run("pytest", "--junitxml=junit.xml")


@nox.session(python=["3.7", "3.8", "3.9"])
def coverage(session):
    # Install deps and the package itself.
    session.install("-r", "requirements-optional.txt")

    session.run("coverage", "run", "-m", "pytest", "--junitxml=junit.xml")
    session.run("coverage", "report", "-m")
    session.run("coverage", "xml")
    session.run("coverage", "html", "-d", "docs/coverage")

    # Generate README badges using genbadge, junit.xml and coverage.xml
    session.install("genbadge[coverage,tests]")
    session.run(
        "genbadge",
        "coverage",
        "-i",
        "coverage.xml",
        "-o",
        "docs/badges/coverage.svg",
    )
    session.run("genbadge", "tests", "-i", "junit.xml", "-o", "docs/badges/tests.svg")
