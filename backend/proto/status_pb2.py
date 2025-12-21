# Generated lightweight protobuf definitions for status service.
from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message_factory as _message_factory
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()

# Build FileDescriptorProto programmatically to avoid requiring protoc at runtime.
_file_proto = _descriptor_pb2.FileDescriptorProto()
_file_proto.name = "status.proto"
_file_proto.package = "svitlyachok"
_file_proto.syntax = "proto3"

_status_request = _file_proto.message_type.add()
_status_request.name = "StatusRequest"
_sr_field = _status_request.field.add()
_sr_field.name = "queue"
_sr_field.number = 1
_sr_field.label = _descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
_sr_field.type = _descriptor_pb2.FieldDescriptorProto.TYPE_STRING

_status_response = _file_proto.message_type.add()
_status_response.name = "StatusResponse"
_ss_field = _status_response.field.add()
_ss_field.name = "status"
_ss_field.number = 1
_ss_field.label = _descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
_ss_field.type = _descriptor_pb2.FieldDescriptorProto.TYPE_BOOL
_ss_field.json_name = "status"

_service = _file_proto.service.add()
_service.name = "StatusService"
_method = _service.method.add()
_method.name = "GetStatus"
_method.input_type = ".svitlyachok.StatusRequest"
_method.output_type = ".svitlyachok.StatusResponse"

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(_file_proto.SerializeToString())

_factory = _message_factory.MessageFactory()

StatusRequest = _factory.GetPrototype(DESCRIPTOR.message_types_by_name["StatusRequest"])
StatusResponse = _factory.GetPrototype(DESCRIPTOR.message_types_by_name["StatusResponse"])

_sym_db.RegisterMessage(StatusRequest)
_sym_db.RegisterMessage(StatusResponse)

__all__ = [
    "StatusRequest",
    "StatusResponse",
    "DESCRIPTOR",
]
