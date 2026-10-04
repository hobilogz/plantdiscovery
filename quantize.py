import onnx
from onnxconverter_common import float16

model_input = "models/plantclef/plantclef24_dinov2.onnx"
model_output = "models/plantclef/plantclef24_dinov2_fp16.onnx"

print("Loading model...")
model = onnx.load(model_input)
print("Converting to float16...")
model_fp16 = float16.convert_float_to_float16(model)
print("Saving model...")
onnx.save(model_fp16, model_output)
print("Done!")
