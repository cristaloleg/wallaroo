

#include <Python.h>
#include "../python-wallaroo.h"

extern PyObject *load_module(char *module_name)
{
  PyObject *pName, *pModule;

  pName = PyUnicode_FromString(module_name);
  /* Error checking of pName left out */

  pModule = PyImport_Import(pName);
  Py_DECREF(pName);

  return pModule;
}

extern char *get_stage_command(PyObject *item)
{
  PyObject *command = PyTuple_GetItem(item, 0);
  char * rtn = PyUnicode_AsUTF8(command);
  Py_DECREF(command);
  return rtn;
}

extern size_t source_decoder_header_length(PyObject *source_decoder)
{
  PyObject *pFunc, *pValue;

  pFunc = PyObject_GetAttrString(source_decoder, "header_length");
  pValue = PyObject_CallFunctionObjArgs(pFunc, NULL);

  size_t sz = PyLong_AsSsize_t(pValue);
  Py_XDECREF(pFunc);
  Py_DECREF(pValue);
  if (sz > 0 && sz < SIZE_MAX) {
    return sz;
  } else {
    return 0;
  }
}

extern size_t source_decoder_payload_length(PyObject *source_decoder, char *bytes, size_t size)
{
  PyObject *pFunc, *pValue, *pBytes;

  pFunc = PyObject_GetAttrString(source_decoder, "payload_length");
  pBytes = PyBytes_FromStringAndSize(bytes, size);
  pValue = PyObject_CallFunctionObjArgs(pFunc, pBytes, NULL);

  size_t sz = PyLong_AsSsize_t(pValue);

  Py_XDECREF(pFunc);
  Py_XDECREF(pBytes);
  Py_XDECREF(pValue);

  /*
  ** NOTE: This doesn't protect us from Python from returning
  **       something bogus like -7.  There is no Python/C API
  **       function to tell us if the Python value is negative.
  */
  if (sz > 0 && sz < SIZE_MAX) {
    return sz;
  } else {
    printf("ERROR: Python payload_length() method returned invalid size\n");
    return 0;
  }
}

extern size_t user_serialization_get_size(PyObject *o)
{
  PyObject *user_bytes = PyObject_CallFunctionObjArgs(g_user_serialization_fn, o, NULL);

  // This will be null if there was an exception.
  if (user_bytes)
  {
    size_t size = PyBytes_Size(user_bytes);
    Py_DECREF(user_bytes);

    // return the size of the buffer plus the 4 bytes needed to record that size.
    return 4 + size;
  }

  return 0;
}

extern void user_serialization(PyObject *o, char *bytes)
{
  PyObject *user_bytes = PyObject_CallFunctionObjArgs(g_user_serialization_fn, o, NULL);

  // This will be null if there was an exception.
  if (user_bytes)
  {
    size_t size = PyBytes_Size(user_bytes);

    unsigned char *ubytes = (unsigned char *) bytes;

    ubytes[0] = (unsigned char)(size >> 24);
    ubytes[1] = (unsigned char)(size >> 16);
    ubytes[2] = (unsigned char)(size >> 8);
    ubytes[3] = (unsigned char)(size);

    memcpy(bytes + 4, PyBytes_AsString(user_bytes), size);

    Py_DECREF(user_bytes);
  }
}


extern int py_unicode_check(PyObject *o)
{
 return PyUnicode_Check(o);
}

extern int py_bytes_check(PyObject *o)
{
 return PyBytes_Check(o);
}

extern size_t py_bytes_or_unicode_size(PyObject *o)
{
  if (PyBytes_Check(o)) {
    return PyBytes_Size(o);
  } else if (PyUnicode_Check(o)) {
    return PyUnicode_GetLength(o);
  }
}

extern char *py_bytes_or_unicode_as_char(PyObject *o)
{
  if (PyBytes_Check(o)) {
    return PyBytes_AsString(o);
  } else if (PyUnicode_Check(o)) {
    return PyUnicode_AsUTF8(o);
  } else{
    return NULL;
  }
}
