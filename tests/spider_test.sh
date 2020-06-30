if [ $# -ne 1 ]
then
    echo "Syntax: ${0} SPIDER_NAME"
    exit 1
else
    SPIDER=${1}
    scrapy list | grep ${SPIDER} > /dev/null
    if [ $? -ne 0 ]
    then
        echo "Error: Spider ${SPIDER} is not found."
        exit 1
    fi
fi

OSTYPE=`uname`

rm -f ${SPIDER}.csv
scrapy crawl ${SPIDER} -t csv -o ${SPIDER}.csv --logfile=${SPIDER}.log

if [ ${OSTYPE} = "Linux" ]
then
    line_count=`grep log_count/ERROR ${SPIDER}.log`
    if [ $? = "0" ]
    then
        exit 1
    else
        exit 0
    fi
elif [ ${OSTYPE} = "Darwin" ]
then
    line_count=`grep log_count/ERROR ${SPIDER}.log`
    if [ $? = "0" ]
    then
        exit 1
    else
        exit 0
    fi
fi
