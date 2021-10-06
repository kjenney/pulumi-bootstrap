git_state_url="https://${GITUB_TOKEN}:x-oauth-basic@api.github.com/repos/kjenney/pulumi-bootstrap/statuses/${sha}"

pylint $(git ls-files '*.py')
if [ $? -eq 0 ]; then
	state="success"
	description="Lint Success"
else
	state="failure"
	description="Lint Failure"
fi
curl -X POST -H \
	"application/json" \
	-d '{"state":"${state}", "description":"${description}", "context":"build/job"}' \
	"${git_state_url}"