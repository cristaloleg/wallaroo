
#ifdef __APPLE__
    #include <AvailabilityMacros.h>
    #if MAC_OS_X_VERSION_MAX_ALLOWED < 101300
        #include <Python/Python.h>
    #else
        #include <Python2.7/Python.h>
    #endif
#else
    #include <python2.7/Python.h>
#endif

#include "../python-wallaroo.h"

extern PyObject *load_module(char *module_name)
{
  PyObject *pName, *pModule;

  pName = PyString_FromString(module_name);
  /* Error checking of pName left out */

  pModule = PyImport_Import(pName);
  Py_DECREF(pName);

  return pModule;
}

extern char *get_stage_command(PyObject *item)
{
  PyObject *command = PyTuple_GetItem(item, 0);
  char * rtn = PyString_AsString(command);
  Py_DECREF(command);
  return rtn;
}

extern size_t source_decoder_header_length(PyObject *source_decoder)
{
  PyObject *pFunc, *pValue;

  pFunc = PyObject_GetAttrString(source_decoder, "header_length");
  pValue = PyObject_CallFunctionObjArgs(pFunc, NULL);

  size_t sz = PyInt_AsSsize_t(pValue);
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

  size_t sz = PyInt_AsSsize_t(pValue);

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
    size_t size = PyString_Size(user_bytes);
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
    size_t size = PyString_Size(user_bytes);

    unsigned char *ubytes = (unsigned char *) bytes;

    ubytes[0] = (unsigned char)(size >> 24);
    ubytes[1] = (unsigned char)(size >> 16);
    ubytes[2] = (unsigned char)(size >> 8);
    ubytes[3] = (unsigned char)(size);

    memcpy(bytes + 4, PyString_AsString(user_bytes), size);

    Py_DECREF(user_bytes);
  }
}

