#!/usr/bin/env python
#
# Copyright (c) 2016 Cisco and/or its affiliates.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os, util
from string import Template

import callback_gen
import dto_gen

jvpp_ifc_template = Template("""
package $plugin_package.$callback_facade_package;

/**
 * <p>Callback Java API representation of $plugin_package plugin.
 * <br>It was generated by jvpp_callback_facade_gen.py based on $inputfile
 * <br>(python representation of api file generated by vppapigen).
 */
public interface CallbackJVpp${plugin_name} extends $base_package.$notification_package.NotificationRegistryProvider, java.lang.AutoCloseable {

    // TODO add send

$methods
}
""")

jvpp_impl_template = Template("""
package $plugin_package.$callback_facade_package;

/**
 * <p>Default implementation of Callback${plugin_name}JVpp interface.
 * <br>It was generated by jvpp_callback_facade_gen.py based on $inputfile
 * <br>(python representation of api file generated by vppapigen).
 */
public final class CallbackJVpp${plugin_name}Facade implements CallbackJVpp${plugin_name} {

    private final $plugin_package.JVpp${plugin_name} jvpp;
    private final java.util.Map<Integer, $base_package.$callback_package.JVppCallback> callbacks;
    private final $plugin_package.$notification_package.${plugin_name}NotificationRegistryImpl notificationRegistry = new $plugin_package.$notification_package.${plugin_name}NotificationRegistryImpl();
    /**
     * <p>Create CallbackJVpp${plugin_name}Facade object for provided JVpp instance.
     * Constructor internally creates CallbackJVppFacadeCallback class for processing callbacks
     * and then connects to provided JVpp instance
     *
     * @param jvpp provided $base_package.JVpp instance
     *
     * @throws java.io.IOException in case instance cannot connect to JVPP
     */
    public CallbackJVpp${plugin_name}Facade(final $base_package.JVppRegistry registry, final $plugin_package.JVpp${plugin_name} jvpp) throws java.io.IOException {
        this.jvpp = java.util.Objects.requireNonNull(jvpp,"jvpp is null");
        this.callbacks = new java.util.HashMap<>();
        java.util.Objects.requireNonNull(registry, "JVppRegistry should not be null");
        registry.register(jvpp, new CallbackJVpp${plugin_name}FacadeCallback(this.callbacks, notificationRegistry));
    }

    @Override
    public $plugin_package.$notification_package.${plugin_name}NotificationRegistry getNotificationRegistry() {
        return notificationRegistry;
    }

    @Override
    public void close() throws Exception {
        jvpp.close();
    }

    // TODO add send()

$methods
}
""")

method_template = Template(
    """    void $name($plugin_package.$dto_package.$request request, $plugin_package.$callback_package.$callback callback) throws $base_package.VppInvocationException;""")

method_impl_template = Template("""    public final void $name($plugin_package.$dto_package.$request request, $plugin_package.$callback_package.$callback callback) throws $base_package.VppInvocationException {
        synchronized (callbacks) {
            callbacks.put(jvpp.$name(request), callback);
        }
    }
""")

no_arg_method_template = Template("""    void $name($plugin_package.$callback_package.$callback callback) throws $base_package.VppInvocationException;""")
no_arg_method_impl_template = Template("""    public final void $name($plugin_package.$callback_package.$callback callback) throws $base_package.VppInvocationException {
        synchronized (callbacks) {
            callbacks.put(jvpp.$name(), callback);
        }
    }
""")


def generate_jvpp(func_list, base_package, plugin_package, plugin_name, dto_package, callback_package, notification_package, callback_facade_package, inputfile):
    """ Generates callback facade """
    print "Generating JVpp callback facade"

    if os.path.exists(callback_facade_package):
        util.remove_folder(callback_facade_package)

    os.mkdir(callback_facade_package)

    methods = []
    methods_impl = []
    for func in func_list:

        if util.is_notification(func['name']) or util.is_ignored(func['name']):
            continue

        camel_case_name = util.underscore_to_camelcase(func['name'])
        camel_case_name_upper = util.underscore_to_camelcase_upper(func['name'])
        if util.is_reply(camel_case_name) or util.is_control_ping(camel_case_name):
            continue

        # Strip suffix for dump calls
        callback_type = get_request_name(camel_case_name_upper, func['name']) + callback_gen.callback_suffix

        if len(func['args']) == 0:
            methods.append(no_arg_method_template.substitute(name=camel_case_name,
                                                             base_package=base_package,
                                                             plugin_package=plugin_package,
                                                             dto_package=dto_package,
                                                             callback_package=callback_package,
                                                             callback=callback_type))
            methods_impl.append(no_arg_method_impl_template.substitute(name=camel_case_name,
                                                                       base_package=base_package,
                                                                       plugin_package=plugin_package,
                                                                       dto_package=dto_package,
                                                                       callback_package=callback_package,
                                                                       callback=callback_type))
        else:
            methods.append(method_template.substitute(name=camel_case_name,
                                                      request=camel_case_name_upper,
                                                      base_package=base_package,
                                                      plugin_package=plugin_package,
                                                      dto_package=dto_package,
                                                      callback_package=callback_package,
                                                      callback=callback_type))
            methods_impl.append(method_impl_template.substitute(name=camel_case_name,
                                                                request=camel_case_name_upper,
                                                                base_package=base_package,
                                                                plugin_package=plugin_package,
                                                                dto_package=dto_package,
                                                                callback_package=callback_package,
                                                                callback=callback_type))

    join = os.path.join(callback_facade_package, "CallbackJVpp%s.java" % plugin_name)
    jvpp_file = open(join, 'w')
    jvpp_file.write(
        jvpp_ifc_template.substitute(inputfile=inputfile,
                                     methods="\n".join(methods),
                                     base_package=base_package,
                                     plugin_package=plugin_package,
                                     plugin_name=plugin_name,
                                     dto_package=dto_package,
                                     notification_package=notification_package,
                                     callback_facade_package=callback_facade_package))
    jvpp_file.flush()
    jvpp_file.close()

    jvpp_file = open(os.path.join(callback_facade_package, "CallbackJVpp%sFacade.java" % plugin_name), 'w')
    jvpp_file.write(jvpp_impl_template.substitute(inputfile=inputfile,
                                                  methods="\n".join(methods_impl),
                                                  base_package=base_package,
                                                  plugin_package=plugin_package,
                                                  plugin_name=plugin_name,
                                                  dto_package=dto_package,
                                                  notification_package=notification_package,
                                                  callback_package=callback_package,
                                                  callback_facade_package=callback_facade_package))
    jvpp_file.flush()
    jvpp_file.close()

    generate_callback(func_list, base_package, plugin_package, plugin_name, dto_package, callback_package, notification_package, callback_facade_package, inputfile)


jvpp_facade_callback_template = Template("""
package $plugin_package.$callback_facade_package;

/**
 * <p>Implementation of JVppGlobalCallback interface for Java Callback API.
 * <br>It was generated by jvpp_callback_facade_gen.py based on $inputfile
 * <br>(python representation of api file generated by vppapigen).
 */
public final class CallbackJVpp${plugin_name}FacadeCallback implements $plugin_package.$callback_package.JVpp${plugin_name}GlobalCallback {

    private final java.util.Map<Integer, $base_package.$callback_package.JVppCallback> requests;
    private final $plugin_package.$notification_package.Global${plugin_name}NotificationCallback notificationCallback;
    private static final java.util.logging.Logger LOG = java.util.logging.Logger.getLogger(CallbackJVpp${plugin_name}FacadeCallback.class.getName());

    public CallbackJVpp${plugin_name}FacadeCallback(final java.util.Map<Integer, $base_package.$callback_package.JVppCallback> requestMap,
                                      final $plugin_package.$notification_package.Global${plugin_name}NotificationCallback notificationCallback) {
        this.requests = requestMap;
        this.notificationCallback = notificationCallback;
    }

    @Override
    public void onError($base_package.VppCallbackException reply) {

        $base_package.$callback_package.JVppCallback failedCall;
        synchronized(requests) {
            failedCall = requests.remove(reply.getCtxId());
        }

        if(failedCall != null) {
            try {
                failedCall.onError(reply);
            } catch(RuntimeException ex) {
                ex.addSuppressed(reply);
                LOG.log(java.util.logging.Level.WARNING, String.format("Callback: %s failed while handling exception: %s", failedCall, reply), ex);
            }
        }
    }

    @Override
    @SuppressWarnings("unchecked")
    public void onControlPingReply(final $base_package.$dto_package.ControlPingReply reply) {

        $base_package.$callback_package.ControlPingCallback callback;
        final int replyId = reply.context;
        synchronized(requests) {
            callback = ($base_package.$callback_package.ControlPingCallback) requests.remove(replyId);
        }

        if(callback != null) {
            callback.onControlPingReply(reply);
        }
    }

$methods
}
""")

jvpp_facade_callback_method_template = Template("""
    @Override
    @SuppressWarnings("unchecked")
    public void on$callback_dto(final $plugin_package.$dto_package.$callback_dto reply) {

        $plugin_package.$callback_package.$callback callback;
        final int replyId = reply.context;
        synchronized(requests) {
            callback = ($plugin_package.$callback_package.$callback) requests.remove(replyId);
        }

        if(callback != null) {
            callback.on$callback_dto(reply);
        }
    }
""")

jvpp_facade_callback_notification_method_template = Template("""
    @Override
    @SuppressWarnings("unchecked")
    public void on$callback_dto($plugin_package.$dto_package.$callback_dto notification) {
        notificationCallback.on$callback_dto(notification);
    }
""")


def generate_callback(func_list, base_package, plugin_package, plugin_name, dto_package, callback_package, notification_package, callback_facade_package, inputfile):
    callbacks = []
    for func in func_list:

        camel_case_name_with_suffix = util.underscore_to_camelcase_upper(func['name'])

        if util.is_ignored(func['name']) or util.is_control_ping(camel_case_name_with_suffix):
            continue

        if util.is_reply(camel_case_name_with_suffix):
            callbacks.append(jvpp_facade_callback_method_template.substitute(plugin_package=plugin_package,
                                                                             dto_package=dto_package,
                                                                             callback_package=callback_package,
                                                                             callback=util.remove_reply_suffix(camel_case_name_with_suffix) + callback_gen.callback_suffix,
                                                                             callback_dto=camel_case_name_with_suffix))

        if util.is_notification(func["name"]):
            with_notification_suffix = util.add_notification_suffix(camel_case_name_with_suffix)
            callbacks.append(jvpp_facade_callback_notification_method_template.substitute(plugin_package=plugin_package,
                                                                             dto_package=dto_package,
                                                                             callback_package=callback_package,
                                                                             callback=with_notification_suffix + callback_gen.callback_suffix,
                                                                             callback_dto=with_notification_suffix))

    jvpp_file = open(os.path.join(callback_facade_package, "CallbackJVpp%sFacadeCallback.java" % plugin_name), 'w')
    jvpp_file.write(jvpp_facade_callback_template.substitute(inputfile=inputfile,
                                                             base_package=base_package,
                                                             plugin_package=plugin_package,
                                                             plugin_name=plugin_name,
                                                             dto_package=dto_package,
                                                             notification_package=notification_package,
                                                             callback_package=callback_package,
                                                             methods="".join(callbacks),
                                                             callback_facade_package=callback_facade_package))
    jvpp_file.flush()
    jvpp_file.close()


# Returns request name or special one from unconventional_naming_rep_req map
def get_request_name(camel_case_dto_name, func_name):
    if func_name in reverse_dict(util.unconventional_naming_rep_req):
        request_name = util.underscore_to_camelcase_upper(reverse_dict(util.unconventional_naming_rep_req)[func_name])
    else:
        request_name = camel_case_dto_name
    return remove_suffix(request_name)


def reverse_dict(map):
    return dict((v, k) for k, v in map.iteritems())


def remove_suffix(name):
    if util.is_reply(name):
        return util.remove_reply_suffix(name)
    else:
        if util.is_dump(name):
            return util.remove_suffix(name, util.dump_suffix)
        else:
            return name