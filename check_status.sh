echo "Testing"
echo $AWS_REGION
echo $commit_sha

f [ -z "$commit_sha" ]
then
      echo "\$commit_sha is empty"
else
      echo "\$commit_sha is NOT empty"
fi

# pylint $(git ls-files '*.py')
# if [ $? -eq 0 ]; then
# 	state="success"
# 	description="Lint Success"
# else
# 	state="failure"
# 	description="Lint Failure"
# fi
# python github/report_status.py $state $description