GITHUB_TOKEN="$1"
COMMIT_SHA="$2"

pylint $(git ls-files '*.py')
if [ $? -eq 0 ]; then
	state="success"
	description="Lint Success"
else
	state="failure"
	description="Lint Failure"
fi
python github/report_status.py $state "$description" $GITHUB_TOKEN $COMMIT_SHA