/*

Copyright 2017 The Wallaroo Authors.

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 implied. See the License for the specific language governing
 permissions and limitations under the License.

*/




PyObject *g_user_deserialization_fn;
PyObject *g_user_serialization_fn;


extern PyObject *application_setup(PyObject *pModule, PyObject *args)
{
  PyObject *pFunc, *pValue;

  pFunc = PyObject_GetAttrString(pModule, "application_setup");
  pValue = PyObject_CallFunctionObjArgs(pFunc, args, NULL);
  Py_DECREF(pFunc);

  printf("C Tuple Check: %d\n", PyTuple_Check(pValue));

  return pValue;
}

extern size_t list_item_count(PyObject *list)
{
  return PyList_Size(list);
}

extern PyObject *get_application_setup_item(PyObject *list, size_t idx)
{
  return PyList_GetItem(list, idx);
}

extern PyObject *get_list_item(PyObject *list, size_t idx)
{
  return PyList_GetItem(list, idx);
}

extern PyObject *source_decoder_decode(PyObject *source_decoder, char *bytes, size_t size)
{
  PyObject *pFunc, *pBytes, *pValue;

  pFunc = PyObject_GetAttrString(source_decoder, "decode");
  pBytes = PyBytes_FromStringAndSize(bytes, size);
  pValue = PyObject_CallFunctionObjArgs(pFunc, pBytes, NULL);

  Py_DECREF(pFunc);
  Py_DECREF(pBytes);

  return pValue;
}

extern PyObject *source_generator_initial_value(PyObject *source_generator)
{
  PyObject *pFunc, *pValue;

  pFunc = PyObject_GetAttrString(source_generator, "initial_value");
  pValue = PyObject_CallFunctionObjArgs(pFunc,  NULL);
  Py_DECREF(pFunc);

  return pValue;
}

extern PyObject *source_generator_apply(PyObject *source_generator, PyObject *data)
{
  PyObject *pFunc, *pValue;

  pFunc = PyObject_GetAttrString(source_generator, "apply");
  pValue = PyObject_CallFunctionObjArgs(pFunc, data, NULL);
  Py_DECREF(pFunc);

  return pValue;
}

extern PyObject *instantiate_python_class(PyObject *class)
{
  return PyObject_CallFunctionObjArgs(class, NULL);
}

extern PyObject *get_name(PyObject *pObject)
{
  PyObject *pFunc, *pValue = NULL;

  pFunc = PyObject_GetAttrString(pObject, "name");
  if (pFunc != NULL) {
    pValue = PyObject_CallFunctionObjArgs(pFunc, NULL);
    Py_DECREF(pFunc);
  }

  return pValue;
}

extern PyObject *computation_compute(PyObject *computation, PyObject *data,
  char* method)
{
  PyObject *pFunc, *pValue;

  pFunc = PyObject_GetAttrString(computation, method);
  pValue = PyObject_CallFunctionObjArgs(pFunc, data, NULL);
  Py_DECREF(pFunc);

  return pValue;
}

extern PyObject *sink_encoder_encode(PyObject *sink_encoder, PyObject *data)
{
  PyObject *pFunc, *pValue;

  pFunc = PyObject_GetAttrString(sink_encoder, "encode");
  pValue = PyObject_CallFunctionObjArgs(pFunc, data, NULL);
  Py_DECREF(pFunc);

  return pValue;
}

extern void py_incref(PyObject *o)
{
  Py_INCREF(o);
}

extern void py_decref(PyObject *o)
{
  Py_DECREF(o);
}

extern PyObject *stateful_computation_compute(PyObject *computation,
  PyObject *data, PyObject *state, char *method)
{
  PyObject *pFunc, *pValue;

  pFunc = PyObject_GetAttrString(computation, method);
  pValue = PyObject_CallFunctionObjArgs(pFunc, data, state, NULL);
  Py_DECREF(pFunc);

  return pValue;
}

extern PyObject *initial_state(PyObject *computation)
{
  PyObject *pFunc, *pState;

  pFunc = PyObject_GetAttrString(computation, "initial_state");
  pState = PyObject_CallFunctionObjArgs(pFunc, NULL);
  Py_DECREF(pFunc);

  return pState;
}

extern long key_hash(PyObject *key)
{
  return PyObject_Hash(key);
}


extern int key_eq(PyObject *key, PyObject* other)
{
  return PyObject_RichCompareBool(key, other, Py_EQ);
}

extern PyObject *extract_key(PyObject *key_extractor, PyObject *data)
{
  PyObject *pFunc, *pValue;

  pFunc = PyObject_GetAttrString(key_extractor, "extract_key");
  pValue = PyObject_CallFunctionObjArgs(pFunc, data, NULL);
  Py_DECREF(pFunc);

  return pValue;
}

extern void set_user_serialization_fns(PyObject *module)
{
  if (PyObject_HasAttrString(module, "deserialize") && PyObject_HasAttrString(module, "serialize"))
  {
    g_user_deserialization_fn = PyObject_GetAttrString(module, "deserialize");
    g_user_serialization_fn = PyObject_GetAttrString(module, "serialize");
  }
  else
  {
    PyObject *wallaroo = PyObject_GetAttrString(module, "wallaroo");
    g_user_deserialization_fn = PyObject_GetAttrString(wallaroo, "deserialize");
    g_user_serialization_fn = PyObject_GetAttrString(wallaroo, "serialize");
    Py_DECREF(wallaroo);
  }
}

extern void *user_deserialization(char *bytes)
{
  unsigned char *ubytes = (unsigned char *)bytes;
  // extract size
  size_t size = (((size_t)ubytes[0]) << 24)
    + (((size_t)ubytes[1]) << 16)
    + (((size_t)ubytes[2]) << 8)
    + ((size_t)ubytes[3]);

  PyObject *py_bytes = PyBytes_FromStringAndSize(bytes + 4, size);
  PyObject *ret = PyObject_CallFunctionObjArgs(g_user_deserialization_fn, py_bytes, NULL);

  Py_DECREF(py_bytes);

  return ret;
}

extern int py_bool_check(PyObject *b)
{
  return PyBool_Check(b);
}

extern int is_py_none(PyObject *o)
{
  return o == Py_None;
}

extern int py_list_check(PyObject *l)
{
  return PyList_Check(l);
}

extern int py_tuple_check(PyObject *t)
{
  return PyTuple_Check(t);
}



