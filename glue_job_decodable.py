import sys
import boto3
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
import cantools

# ------------------------------------------------------------------------------
# AWS Glue job script to decode CAN DBC encoded binary files
#
# Required job parameters:
#   --JOB_NAME           Name of the Glue job (handled automatically by Glue)
#   --DBC_S3_PATH        S3 URI (s3://bucket/path) pointing to the DBC file
#   --INPUT_S3_PATH      S3 URI pointing to a folder or prefix containing the
#                        binary encoded files (.bin). All files under the
#                        prefix will be processed.
#   --OUTPUT_S3_PATH     S3 URI where the decoded results will be written.
#
# Optional parameters (set via Spark configuration):
#   spark.files.maxPartitionBytes  Size in bytes of input data per partition. Increase
#                                  this to group multiple small files into a single
#                                  partition. See accompanying report for guidance.
#   spark.files.openCostInBytes    Estimated cost to open a file in bytes. Larger values
#                                  encourage grouping many files into one partition.
#
# This script demonstrates how to:
#   1. Load a DBC file from S3 and broadcast it to executors.
#   2. Read binary files from S3 using the binaryFile data source.
#   3. Apply mapPartitions to decode each binary file with the DBC definitions.
#   4. Write a summary of decoded results to S3 in CSV format.
#
# It is tailored for the sample_decodable.dbc / sample_decodable.bin provided
# in the accompanying materials. Each binary file consists of repeated 12-byte
# frames: 4 bytes little‑endian message identifier followed by an 8‑byte
# payload. The DBC defines a message with ID 256 and a single 8-bit signal
# called "ExampleSignal" located at the first byte of the payload.
#
# The decode logic extracts all frames in each file, decodes the signal using
# cantools, and outputs aggregated metrics per file: total number of frames,
# minimum ExampleSignal value, and maximum ExampleSignal value. Adjust this
# logic as needed to meet your analysis needs.
# ------------------------------------------------------------------------------


def load_dbc_from_s3(s3_uri: str) -> str:
    """Read DBC file content from S3 and return as string."""
    if not s3_uri.startswith("s3://"):
        raise ValueError("DBC_S3_PATH must be an s3 URI, e.g. s3://bucket/path/to/file.dbc")
    path = s3_uri[5:]
    bucket, key = path.split('/', 1)
    s3_client = boto3.client('s3')
    response = s3_client.get_object(Bucket=bucket, Key=key)
    return response['Body'].read().decode('utf-8')


def decode_partition(rows_iter, broadcast_db):
    """
    Decode a batch of binary files contained in a single partition. Each file is
    represented by a single row with fields `path` and `content`.  This
    function extracts CAN frames from the raw binary content using the
    following frame format:

      - 4 bytes: little‑endian unsigned integer representing the CAN
        identifier.  In our test data this value is 256 (0x100).
      - 8 bytes: payload (data bytes).  The ExampleSignal is stored in
        byte 0 of the payload.

    The cantools Database broadcast via `broadcast_db` is used to decode
    each frame.  To keep the result compact and avoid returning millions of
    rows, this function aggregates the decoded signal values per file,
    computing the number of frames, the minimum ExampleSignal value and the
    maximum ExampleSignal value encountered.

    Parameters
    ----------
    rows_iter : iterable
        An iterator over rows in this partition.  Each row is a PySpark
        Row with schema defined by the binaryFile source (path, length,
        content, modificationTime).

    broadcast_db : pyspark.broadcast.Broadcast
        A broadcasted cantools Database used to decode frames.

    Yields
    ------
    tuple
        (file_path, frame_count, min_example_signal, max_example_signal)
    """
    db = broadcast_db.value
    for row in rows_iter:
        file_path = row['path']
        content = row['content']
        frame_size = 4 + 8
        total_bytes = len(content)
        frame_count = total_bytes // frame_size
        min_signal = None
        max_signal = None
        offset = 0
        for _ in range(frame_count):
            msg_id_bytes = content[offset: offset + 4]
            payload = content[offset + 4: offset + frame_size]
            offset += frame_size
            msg_id = int.from_bytes(msg_id_bytes, byteorder='little', signed=False)
            try:
                decoded = db.decode_message(msg_id, payload)
                val = decoded.get('ExampleSignal')
                if val is not None:
                    if min_signal is None or val < min_signal:
                        min_signal = val
                    if max_signal is None or val > max_signal:
                        max_signal = val
            except Exception:
                # Skip frames that can't be decoded
                continue
        if min_signal is None:
            min_signal = 0
        if max_signal is None:
            max_signal = 0
        yield (file_path, frame_count, min_signal, max_signal)


def main():
    # Parse parameters
    args = getResolvedOptions(sys.argv,
                              ['JOB_NAME', 'DBC_S3_PATH', 'INPUT_S3_PATH', 'OUTPUT_S3_PATH'])

    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark = glue_context.spark_session

    # Load DBC and broadcast
    dbc_text = load_dbc_from_s3(args['DBC_S3_PATH'])
    database = cantools.database.load_string(dbc_text)
    broadcast_db = sc.broadcast(database)

    # Read binary files from S3
    binary_df = spark.read.format("binaryFile").load(args['INPUT_S3_PATH'])

    # Apply decoding per partition
    decoded_rdd = binary_df.rdd.mapPartitions(lambda rows: decode_partition(rows, broadcast_db))
    decoded_df = decoded_rdd.toDF(["file_path", "frame_count", "min_example_signal", "max_example_signal"])

    # Write result to S3
    decoded_df.write.mode("overwrite").csv(args['OUTPUT_S3_PATH'])

    sc.stop()


if __name__ == '__main__':
    main()