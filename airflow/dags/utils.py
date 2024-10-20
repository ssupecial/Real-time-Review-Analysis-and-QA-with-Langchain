import re
import boto3
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
from airflow.models import Variable
from botocore.exceptions import ClientError

class S3NewFileSensor(BaseSensorOperator):
    """
    커스텀 S3 Sensor: 새로운 파일이 추가되었는지 감지
    """
    
    @apply_defaults
    def __init__(self, bucket_name, prefix="", aws_conn_id='aws_default', variable="s3_file_list", *args, **kwargs):
        super(S3NewFileSensor, self).__init__(*args, **kwargs)
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.aws_conn_id = aws_conn_id
        self.hook = None
        self.variable = variable
        self.existing_files = set()

    def _get_processed_files(self):
        """
        Airflow Variable에서 기존 파일 목록 가져오기
        """
        return Variable.get(self.variable, default_var=[], deserialize_json=True)
    
    def _extract_file_number(self, file_name):
        """
        파일 이름에서 숫자 추출
        """
        match = re.search(r'\d+', file_name)
        return int(match.group()) if match else -1

    def poke(self, context):
        """
        S3 버킷에서 새로운 파일이 있는지 확인
        """
        s3 = boto3.client('s3')

        try:
            # 버킷 내 객체 목록 가져오기
            response = s3.list_objects_v2(Bucket=self.bucket_name, Prefix=self.prefix)

            # 버킷에 객체가 있을 때만 처리
            if 'Contents' in response:
                file_list = [content["Key"] for content in response["Contents"]]
                file_list_number = [self._extract_file_number(file) for file in file_list if self._extract_file_number(file) != -1]
                previous_files_number = self._get_processed_files()
                new_files_number = set(file_list_number) - set(previous_files_number)

                # 새로운 파일이 있는 경우
                if new_files_number:
                    self.log.info(f"새로운 파일이 {len(new_files_number)}개 발견되었습니다.")
                    self.log.info(f"새로운 파일 index 목록: {new_files_number}")
                    
                    # 새로운 파일 중 가장 작은 index를 찾아서 반환
                    new_file_index = sorted(new_files_number)[0]
                    self.log.info(f"새로운 파일 index: {new_file_index}")
                    context['ti'].xcom_push(key='new_file_index', value=new_file_index)
                    return True

            self.log.info("새로운 파일을 찾지 못했습니다. 다시 시도 중...")
            return False

        except ClientError as e:
            self.log.error(f"S3 버킷 목록 가져오기 실패: {e}")
            return False
