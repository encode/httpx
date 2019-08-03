import nox


@nox.session(python=["3.6", "3.7", "3.8"])
def tests(session):
    session.install("-r", "requirements.txt")
    session.install(".")
    session.run('pytest')
