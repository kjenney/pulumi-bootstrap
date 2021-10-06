echo "Testing"
echo $AWS_REGION
echo $commit-sha

if [ -z "$commit-sha" ]
then
      echo "\$commit-sha is empty"
else
      echo "\$commit-sha is NOT empty"
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