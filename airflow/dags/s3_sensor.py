import boto3
from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
from botocore.exceptions import ClientError

class S3NewFileSensor(BaseSensorOperator):
    """
    커스텀 S3 Sensor: 새로운 파일이 추가되었는지 감지
    """
    
    @apply_defaults
    def __init__(self, bucket_name, prefix="", aws_conn_id='aws_default', *args, **kwargs):
        super(S3NewFileSensor, self).__init__(*args, **kwargs)
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.aws_conn_id = aws_conn_id
        self.hook = None
        self.existing_files = set()

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
                current_files = set([obj['Key'] for obj in response['Contents']])

                # 기존 파일과 비교해 새로운 파일이 있는지 확인
                new_files = current_files - self.existing_files

                if new_files:
                    self.log.info(f"새로운 파일 발견: {new_files}")
                    return True  # 새로운 파일이 감지됨
                
                # 기존 파일 목록 업데이트
                self.existing_files = current_files

            self.log.info("새로운 파일을 찾지 못했습니다. 다시 시도 중...")
            return False

        except ClientError as e:
            self.log.error(f"S3 버킷 목록 가져오기 실패: {e}")
            return False
